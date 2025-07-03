
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from typing import List, Tuple, Optional
import asyncio
import time


class LegalAssistant:
    def __init__(self):
        load_dotenv()
        
        # Role instruction
        self.role_instruction = (
            "You are a legal assistant strictly limited to the provided legal context from Indian law. "
            "Do not use external knowledge beyond the given context. "
            "Support the user based solely on the embedded context supplied. "
            "Provide legal procedures, actions, rights, and remedies with relevant law sections "
            "only if explicitly supported by the context. "
            "If context is insufficient, respond: 'I am a continual learning AI assistant. "
            "Waseem has not yet trained me enough to provide a complete answer. "
            "I will be retrained soon with updated knowledge. Apologies.'"
        )
        
        # Initialize components
        self.vector_store = Chroma(
            embedding_function=MistralAIEmbeddings(model="mistral-embed"),
            persist_directory='./indian_law_vector_store',
            collection_name='indian_law_docs'
        )
        
        self.model = ChatMistralAI(model="mistral-small-latest", temperature=0.1)
        self.chat_history: List[HumanMessage | AIMessage] = []
        self.max_history_length = 10  # Limit history to prevent context overflow
        
        # Create prompt template once
        self.prompt_template = ChatPromptTemplate([
            ("system", self.role_instruction),
            MessagesPlaceholder(variable_name="chat_history"),
            ("user", self._create_user_prompt_template())
        ])
    
    def _create_user_prompt_template(self) -> str:
        return (
            "Context from Indian law documents:\n{context}\n\n"
            "User query: {user_query}\n\n"
            "Please answer based only on the retrieved context above. "
            "If the context doesn't contain sufficient information, "
            "use the standard insufficient context response."
        )
    
    def _format_metadata(self, meta: dict) -> str:
        """Format document metadata for display"""
        section = meta.get('section', 'N/A')
        section_title = meta.get('section_title', 'N/A')
        law_name = meta.get('law_name', 'N/A')
        chapter_title = meta.get('chapter_title', 'N/A')
        return f"Section: {section} | Title: {section_title} | Law: {law_name} | Chapter: {chapter_title}"
    
    def _extract_metadata_filters(self, query: str) -> dict:
        """Extract possible metadata filters from the user query."""
        filters = {}
        # Simple extraction: look for section numbers, law names, or chapter titles
        import re
        section_match = re.search(r'section\s*(\d+)', query, re.IGNORECASE)
        if section_match:
            filters['section'] = section_match.group(1)
        # Add more sophisticated extraction as needed
        # Example: look for 'Indian Penal Code' or similar law names
        if 'indian penal code' in query.lower():
            filters['law_name'] = 'Indian Penal Code, 1860'
        # Example: look for chapter titles (very basic)
        if 'offences affecting the human body' in query.lower():
            filters['chapter_title'] = 'offences affecting the human body'
        return filters

    def _search_documents(self, query: str, k: int = 5) -> List[Tuple]:
        """Search for relevant documents in vector store, with metadata filtering if possible."""
        try:
            filters = self._extract_metadata_filters(query)
            if filters:
                print(f"[DEBUG] Using metadata filters: {filters}")
                results = self.vector_store.similarity_search_with_score(query, k=k, filter=filters)
            else:
                results = self.vector_store.similarity_search_with_score(query, k=k)
            return results
        except Exception as e:
            print(f"[ERROR] Vector search failed: {e}")
            return []
    
    def _format_context(self, results: List[Tuple]) -> str:
        """Format search results into context string"""
        if not results:
            return "No relevant legal documents found."
        
        context_parts = []
        for doc, score in results:
            metadata_str = self._format_metadata(doc.metadata)
            context_parts.append(
                f"{metadata_str}\n"
                f"Relevance Score: {score:.2f}\n"
                f"Content: {doc.page_content}\n"
                f"{'-' * 50}"
            )
        
        return "\n\n".join(context_parts)
    
    def _manage_chat_history(self):
        """Manage chat history length to prevent context overflow"""
        if len(self.chat_history) > self.max_history_length:
            # Keep only the most recent messages
            self.chat_history = self.chat_history[-self.max_history_length:]
    
    def _generate_search_keywords(self, query: str) -> str:
        """Generate better search keywords from user query"""
        # Simple keyword extraction - can be enhanced with NLP
        legal_keywords = [
            'section', 'act', 'law', 'court', 'legal', 'procedure', 'rights',
            'remedy', 'civil', 'criminal', 'constitutional', 'contract',
            'property', 'family', 'labour', 'corporate', 'tax'
        ]
        
        query_lower = query.lower()
        # If query already contains legal terms, use as-is
        if any(keyword in query_lower for keyword in legal_keywords):
            return query
        
        # Otherwise, try to enhance with legal context
        return f"{query} legal procedure rights"
    
    async def _get_llm_response(self, context: str, user_query: str) -> str:
        """Get response from LLM with context"""
        try:
            prompt = self.prompt_template.invoke({
                "chat_history": self.chat_history,
                "context": context,
                "user_query": user_query
            })
            
            response = await asyncio.to_thread(self.model.invoke, prompt)
            return response.content
        
        except Exception as e:
            print(f"[ERROR] LLM invocation failed: {e}")
            return (
                "I apologize, but I encountered an error while processing your request. "
                "Please try rephrasing your question."
            )
    
    async def process_query(self, user_query: str) -> str:
        """Process user query and return response"""
        start_time = time.time()
        
        # Generate search keywords
        search_query = self._generate_search_keywords(user_query)
        
        # Search for relevant documents
        search_results = self._search_documents(search_query)
        
        # If no results, try with original query
        if not search_results and search_query != user_query:
            search_results = self._search_documents(user_query)
        
        # Format context
        context = self._format_context(search_results)
        
        # Get LLM response
        ai_response = await self._get_llm_response(context, user_query)
        
        # Update chat history
        self.chat_history.append(HumanMessage(content=user_query))
        self.chat_history.append(AIMessage(content=ai_response))
        
        # Manage history length
        self._manage_chat_history()
        
        processing_time = time.time() - start_time
        print(f"[INFO] Query processed in {processing_time:.2f} seconds")
        
        return ai_response
    
    def get_clarification(self, original_query: str) -> str:
        """Generate clarification prompt for unclear queries"""
        return (
            f"I couldn't find specific legal information for your query: '{original_query}'\n\n"
            "To help you better, could you please:\n"
            "1. Specify the area of law (civil, criminal, family, corporate, etc.)\n"
            "2. Mention any specific acts or sections if known\n"
            "3. Provide more context about your legal situation\n\n"
            "Please rephrase your question with more details."
        )


async def main():
    """Main chat loop"""
    assistant = LegalAssistant()
    
    print("=== Indian Legal Assistant ===")
    print("Type 'exit' to end the chat.")
    print("Type 'clear' to clear chat history.")
    print("=" * 40)
    
    while True:
        try:
            user_input = input("\nEnter your legal query: ").strip()
            
            if user_input.lower() == 'exit':
                print("Thank you for using the Legal Assistant. Goodbye!")
                break
            
            if user_input.lower() == 'clear':
                assistant.chat_history.clear()
                print("Chat history cleared.")
                continue
            
            if not user_input:
                print("Please enter a valid query.")
                continue
            
            print("\n" + "="*50)
            print("USER QUERY:")
            print(user_input)
            print("="*50)
            
            # Process query
            response = await assistant.process_query(user_input)
            
            print("\nLEGAL ASSISTANT RESPONSE:")
            print("-" * 30)
            print(response)
            print("="*50)
            
        except KeyboardInterrupt:
            print("\n\nChat interrupted by user. Goodbye!")
            break
        except Exception as e:
            print(f"\n[ERROR] Unexpected error: {e}")
            print("Please try again with a different query.")


def run_assistant():
    """Run the assistant with proper async handling"""
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"Failed to start assistant: {e}")


if __name__ == "__main__":
    run_assistant()