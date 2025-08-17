from tools.patch_sqlite import patch_sqlite  # Import the patch before any other imports

from langgraph.graph import StateGraph, START, END
from typing import TypedDict, Annotated
from langchain_core.messages import BaseMessage, HumanMessage, SystemMessage, AIMessage
from langchain_mistralai import ChatMistralAI
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.graph.message import add_messages
from dotenv import load_dotenv
from langchain.tools import Tool
from langgraph.prebuilt import ToolNode
from langgraph.prebuilt import tools_condition
from tools.vector_search_tool import chroma_search_with_score
from tools.online_search_tool import OnlineSearchTool
from tools.summarization_tool import SummarizationTool
import re

# --- System Prompt ---
SYSTEM_PROMPT = SystemMessage(content="""
You are Jurisol, a sophisticated AI-powered legal assistant with deep expertise in Indian Law and legal research.

🧠 CORE CAPABILITIES:
1. Legal Research & Analysis
   - Access to Indian legal databases and government sources
   - Ability to analyze case law, statutes, and legal documents
   - Integration of multiple legal sources into cohesive insights

2. Query Processing
   - Natural language understanding of legal questions
   - Context-aware response generation
   - Identification of relevant legal principles and precedents

3. Source Integration & Synthesis
   When working with legal sources (whether from vector search or online):
   - Automatically evaluate source credibility and relevance
   - Extract key legal principles and holdings
   - Connect findings to the user's specific situation
   - Synthesize information into actionable insights

📚 RESPONSE METHODOLOGY:
For every query, follow this integrated approach:
1. Context Analysis
   - Identify the legal domain and key issues
   - Frame the question within relevant Indian legal framework
   
2. Source Evaluation
   - Assess credibility and relevance of available sources
   - Extract pertinent legal principles and precedents
   - Connect sources to establish legal narrative

3. Legal Application
   - Apply extracted principles to the specific query
   - Consider practical implications and limitations
   - Identify relevant statutory provisions or case law

4. Synthesis & Presentation
   - Present findings in clear, structured format
   - Support conclusions with specific legal references
   - Highlight practical implications and next steps

🚫 BOUNDARIES:
- Strictly Indian law context only
- No speculation on rulings or citations
- Focus on information and analysis, not direct advice

🎯 OUTPUT STYLE:
Maintain a professional, authoritative tone while ensuring:
- Clear structure and logical flow
- Proper citation of legal sources
- Balanced analysis of legal principles
- Practical context and implications
- Actionable insights for further research

For casual greetings or non-legal conversations, respond naturally and professionally while being ready to assist with legal matters.

Remember: You are not just providing information, but offering sophisticated legal analysis integrated with source materials. Each response should demonstrate your ability to synthesize complex legal information into clear, actionable insights.""")

# Load environment variables from .env file
load_dotenv()

# Initialize the LLM with the Mistral model
llm = ChatMistralAI(
    model_name="mistral-small-latest",
    temperature=0.1,
    streaming=True,
    max_tokens=2048
)

# Define the state for the chat node
class ChatState(TypedDict):
    messages: Annotated[list[BaseMessage], add_messages]

def is_legal_query(query: str) -> bool:
    """
    Determine if a query requires legal research or is just casual conversation
    """
    query_lower = query.lower().strip()
    
    # Casual conversation patterns
    casual_patterns = [
        r'^(hi|hello|hey|good morning|good afternoon|good evening)',
        r'^(my name is|i am|i\'m)',
        r'^(how are you|what\'s up|sup)',
        r'^(thank you|thanks|bye|goodbye)',
        r'^(can you help|what can you do)',
        r'^(test|testing)',
    ]
    
    # Check if it matches casual patterns
    for pattern in casual_patterns:
        if re.match(pattern, query_lower):
            print(f"[DEBUG] Casual query detected: {query[:50]}...")
            return False
    
    # Legal keywords that indicate need for search
    legal_keywords = [
        'law', 'legal', 'court', 'judge', 'case', 'section', 'act', 'constitution',
        'rights', 'duty', 'obligation', 'contract', 'agreement', 'property',
        'criminal', 'civil', 'family', 'divorce', 'marriage', 'inheritance',
        'business', 'company', 'registration', 'license', 'permit', 'tax',
        'labour', 'employment', 'salary', 'wages', 'dispute', 'complaint',
        'police', 'arrest', 'bail', 'custody', 'evidence', 'witness',
        'appeal', 'petition', 'suit', 'hearing', 'trial', 'verdict',
        'ipc', 'crpc', 'cpc', 'indian penal code', 'constitution of india',
        'supreme court', 'high court', 'district court', 'magistrate'
    ]
    
    # Check if query contains legal keywords
    has_legal_keywords = any(keyword in query_lower for keyword in legal_keywords)
    
    # If query is longer than 10 words and no legal keywords, probably still legal
    word_count = len(query.split())
    is_complex_query = word_count > 10
    
    is_legal = has_legal_keywords or is_complex_query
    
    print(f"[DEBUG] Query analysis: '{query[:50]}...' -> Legal: {is_legal} (keywords: {has_legal_keywords}, complex: {is_complex_query})")
    
    return is_legal

def process_search_results(search_results) -> str:
    """
    Process search results handling different return types (string, dict, list, etc.)
    """
    if not search_results:
        return ""
    
    try:
        # Handle different return types from search tools
        if isinstance(search_results, str):
            return search_results.strip()
        elif isinstance(search_results, dict):
            # If it's a dict, try to extract meaningful content
            if 'content' in search_results:
                content = search_results['content']
                return str(content).strip() if content else ""
            elif 'results' in search_results:
                results = search_results['results']
                if isinstance(results, list):
                    return '\n'.join([str(item) for item in results if item])
                return str(results).strip() if results else ""
            elif 'text' in search_results:
                return str(search_results['text']).strip()
            else:
                # Convert entire dict to string as fallback
                return str(search_results).strip()
        elif isinstance(search_results, list):
            # If it's a list, join the elements
            return '\n'.join([str(item) for item in search_results if item])
        else:
            # For any other type, convert to string
            return str(search_results).strip()
    except Exception as e:
        print(f"[DEBUG] Error processing search results: {e}")
        return ""

def get_enhanced_response_with_search(query: str, messages: list) -> str:
    """
    Enhanced response generation with legal document search
    """
    print(f"[DEBUG] Performing legal research for: {query[:50]}...")
    
    context = ""
    
    try:
        # Try vector search first
        raw_search_results = search_indian_law_documents_wrapped.func(query)
        print(f"[DEBUG] Raw vector search results type: {type(raw_search_results)}")
        print(f"[DEBUG] Raw vector search results: {str(raw_search_results)[:200]}...")
        
        search_results = process_search_results(raw_search_results)
        print(f"[DEBUG] Processed vector search results: {bool(search_results and search_results.strip())}")
        
        if search_results and search_results.strip():
            context = f"Based on the Indian legal documents:\n{search_results}\n\n"
            print(f"[DEBUG] Using vector search results")
        else:
            print(f"[DEBUG] Vector search yielded no usable results, trying online search")
            # If no vector results, try online search
            try:
                raw_online_results = online_search_tool_wrapped.func(query)
                print(f"[DEBUG] Raw online search results type: {type(raw_online_results)}")
                
                online_results = process_search_results(raw_online_results)
                print(f"[DEBUG] Processed online search results: {bool(online_results and online_results.strip())}")
                
                if online_results and online_results.strip():
                    context = f"Based on the online search results:\n{online_results}\n\n"
                    print(f"[DEBUG] Using online search results")
            except Exception as e:
                print(f"[DEBUG] Online search failed: {e}")
    
    except Exception as e:
        print(f"[DEBUG] Vector search failed: {e}")
        context = ""
    
    # Create enhanced prompt with context
    try:
        if context:
            enhanced_prompt = (
                f"{context}\n"
                "Please provide a detailed answer to the user's question about Indian law. "
                "Include specific references to relevant constitutional articles, sections, or legal precedents. "
                "Make sure the response is well-structured and easy to understand."
            )
            
            # Add enhanced prompt to messages
            enhanced_messages = messages + [HumanMessage(content=enhanced_prompt)]
            response = llm.invoke(enhanced_messages)
            print(f"[DEBUG] Enhanced LLM response generated successfully")
            
        else:
            # No search results found, use direct response
            print(f"[DEBUG] No search results found, using direct response")
            response = llm.invoke(messages)
        
        return response
        
    except Exception as e:
        print(f"[DEBUG] Error generating response: {e}")
        # Return a basic response in case of any error
        basic_messages = [
            SystemMessage(content="You are Jurisol, a helpful legal assistant specializing in Indian law."),
            HumanMessage(content=query)
        ]
        return llm.invoke(basic_messages)

def get_direct_response(messages: list) -> str:
    """
    Direct response without search for casual queries
    """
    print(f"[DEBUG] Generating direct response for casual query")
    response = llm.invoke(messages)
    return response

# Define the tool calling function with intelligent query classification
def tool_calling_llm(state: ChatState):
    messages = state["messages"]
    
    if not messages:
        return {"messages": [AIMessage(content="Hello! I'm Jurisol, your AI legal assistant. How can I help you with Indian law today?")]}
    
    # Get the user's query
    user_query = messages[-1].content
    print(f"[DEBUG] Processing query: {user_query[:100]}...")
    
    # Determine if this requires legal research
    needs_legal_search = is_legal_query(user_query)
    
    # Prepare system message and user messages
    system_message = SystemMessage(content=SYSTEM_PROMPT.content)
    conversation_messages = [system_message] + messages
    
    try:
        if needs_legal_search:
            print(f"[DEBUG] Legal query detected, performing research...")
            # Perform legal research and enhanced response
            response = get_enhanced_response_with_search(user_query, conversation_messages)
        else:
            print(f"[DEBUG] Casual query detected, direct response...")
            # Direct conversational response
            response = get_direct_response(conversation_messages)
        
        # Validate response
        if response and hasattr(response, 'content') and response.content.strip():
            print(f"[DEBUG] Response generated successfully: {response.content[:100]}...")
            return {"messages": [response]}
        else:
            # Fallback response
            print(f"[DEBUG] Invalid response, using fallback")
            fallback_response = llm.invoke([
                SystemMessage(content="You are Jurisol, a helpful legal assistant specializing in Indian law."),
                HumanMessage(content=user_query)
            ])
            
            if fallback_response and hasattr(fallback_response, 'content'):
                return {"messages": [fallback_response]}
            else:
                # Ultimate fallback
                ultimate_fallback = AIMessage(content="I understand you're asking about legal matters. Could you please rephrase your question so I can assist you better?")
                return {"messages": [ultimate_fallback]}
            
    except Exception as e:
        print(f"[DEBUG] Error in tool_calling_llm: {e}")
        import traceback
        print(f"[DEBUG] Full traceback: {traceback.format_exc()}")
        
        # Error fallback with more specific message
        try:
            error_response = llm.invoke([
                SystemMessage(content="You are Jurisol, a legal assistant. Acknowledge the user's legal question and provide a helpful response."),
                HumanMessage(content=f"The user asked: {user_query}")
            ])
            return {"messages": [error_response]}
        except Exception as e2:
            print(f"[DEBUG] Even fallback failed: {e2}")
            # Ultimate error fallback
            final_fallback = AIMessage(content="I apologize for the technical difficulty. I'm here to help with Indian legal questions. Please try rephrasing your question, and I'll do my best to assist you.")
            return {"messages": [final_fallback]}

# Define the tools with their wrapped functions
online_search_tool_wrapped = Tool(
    name="online_search_tool",
    description="Search and summarize Indian government websites for a given query.",
    func=OnlineSearchTool(llm)
)

search_indian_law_documents_wrapped = Tool(
    name="search_indian_law_documents",
    description="Search the Indian law vector store for relevant legal documents and provisions.",
    func=chroma_search_with_score
)

summarization_tool_wrapped = Tool(
    name="summarization_tool",
    description="Summarize the provided text into concise legal insights.",
    func=SummarizationTool(llm)
)

# Bind the tools to the LLM
tools = [online_search_tool_wrapped, search_indian_law_documents_wrapped, summarization_tool_wrapped]
llm_with_tools = llm.bind_tools(tools)

# Checkpointer
checkpointer = InMemorySaver()

# Define the state graph for the chatbot
builder = StateGraph(ChatState)
builder.add_node("tool_calling_llm", tool_calling_llm)
builder.add_node("tools", ToolNode(tools))

# Add Edges
builder.add_edge(START, "tool_calling_llm")
builder.add_conditional_edges(
    "tool_calling_llm",
    tools_condition
)
builder.add_edge("tools", "tool_calling_llm")

# Compile the chatbot with the defined state graph and checkpointer
chatbot = builder.compile(checkpointer=checkpointer)