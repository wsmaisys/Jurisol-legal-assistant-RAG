from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain.schema.runnable import RunnableSequence, RunnableBranch
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage
from dotenv import load_dotenv
from pydantic import BaseModel, ValidationError
import re


def main():
    load_dotenv()

    role_instruction = (
        "You are a legal assistant strictly limited to the provided legal context extracted from Indian law. "
        "Do not use any external knowledge or assumptions beyond the context given. "
        "Your role is to support the user’s side based solely on the embedded context supplied. "
        "Advise the user on what will be the legal procedures to be followed now, "
        "including the possible legal actions, rights, and remedies available, along with any relevant sections of the law, "
        "but only if such guidance is explicitly supported by the context. "
        "If the context is insufficient to answer, respond with: "
        "'I am a continual learning AI assistant, Waseem has not yet trained me enough to provide all the answer. "
        "Shortly, I will be retrained and my memory will be updated to answer further. Apologies' "
        "Do not speculate or answer beyond the context under any circumstance."
    )

    # Load the existing vector store
    vector_store = Chroma(
        embedding_function=MistralAIEmbeddings(model="mistral-embed"),
        persist_directory='./indian_law_vector_store',
        collection_name='indian_law_docs'
    )

    def format_metadata(meta):
        section = meta.get('section', '')
        section_title = meta.get('section_title', '')
        law_name = meta.get('law_name', '')
        chapter_title = meta.get('chapter_title', '')
        return f"Section: {section} | Title: {section_title} | Law: {law_name} | Chapter: {chapter_title}"

    # LLM and chat setup
    model = ChatMistralAI(model="mistral-small-latest", temperature=0.1)
    chat_history = []

    print("Type 'exit' to end the chat.\n")
    while True:
        user_query = input("Enter your legal query: ")
        if user_query.strip().lower() == 'exit':
            print("Exiting chat.")
            break

        # Step 1: Let LLM decide if/what to search
        search_agent_prompt = (
            f"{role_instruction}\n"
            "You are to decide if a search in the Indian law database is needed to answer the user's query. "
            "If yes, suggest the most relevant keywords or a refined query for the search. "
            "If possible, also suggest a metadata filter in JSON (e.g., {'law_name': 'Indian Penal Code, 1860'}). "
            "If not, say you cannot answer.\n"
            f"User query: {user_query}\n"
            "Respond in JSON: {{'search': true/false, 'search_query': '...', 'metadata_filter': {{...}}, 'answer': '...'}}"
        )

        agent_response = model.invoke(search_agent_prompt)

        class SearchAgentResponse(BaseModel):
            search: bool
            search_query: str = ""
            metadata_filter: dict = {}

        def extract_json(text):
            text = re.sub(r"^```[a-zA-Z]*", "", text.strip())
            text = re.sub(r"```$", "", text.strip())
            match = re.search(r"\{[\s\S]*\}", text)
            if match:
                return match.group(0)
            return text

        print("\n[DEBUG] Raw LLM response for search agent:")
        print(agent_response.content)

        try:
            json_str = extract_json(agent_response.content)
            print("[DEBUG] Extracted JSON string:")
            print(json_str)
            agent_json = SearchAgentResponse.model_validate_json(json_str)
            print("[DEBUG] Parsed Pydantic object:")
            print(agent_json)
        except ValidationError as ve:
            print("[WARN] Validation error:", ve)
            agent_json = SearchAgentResponse(search=False, search_query="", metadata_filter={})
        except Exception as e:
            print("[WARN] Could not parse LLM response. Error:", e)
            agent_json = SearchAgentResponse(search=False, search_query="", metadata_filter={})

        clarification_attempted = False
        while True:
            if agent_json.search:
                search_query = agent_json.search_query or user_query
                metadata_filter = agent_json.metadata_filter if hasattr(agent_json, 'metadata_filter') else {}

                # ✅ SAFE & CORRECT FILTER FORMAT FOR CHROMA
                valid_metadata_filter = {
                    k: v for k, v in metadata_filter.items()
                    if isinstance(v, (str, int, float, list))
                }

                chroma_filter = None
                if valid_metadata_filter:
                    chroma_filter = {
                        "where": {
                            "$eq": valid_metadata_filter
                        }
                    }

                print(f"[DEBUG] Final chroma_filter: {chroma_filter}")
                try:
                    if chroma_filter:
                        results = vector_store.similarity_search_with_score(search_query, k=5, filter=chroma_filter)
                    else:
                        results = vector_store.similarity_search_with_score(search_query, k=5)
                except Exception as e:
                    print(f"[ERROR] Search failed: {e}")
                    results = []

                if not results:
                    if clarification_attempted:
                        print("\n--- User Query ---\n")
                        print(user_query)
                        print("\n--- LLM Response ---\n")
                        print("Sorry, no relevant legal information could be found even after clarification.")
                        ai_message = "Sorry, no relevant legal information could be found even after clarification."
                        break
                    print("\nNo relevant documents found. Please clarify or rephrase your query:")
                    user_query = input("Clarify your legal query: ")
                    clarification_attempted = True
                    continue

                context = "\n\n".join([
                    f"{format_metadata(doc.metadata)}\nSimilarity Score: {score:.2f}\nText: {doc.page_content}"
                    for doc, score in results
                ])

                prompt_template = ChatPromptTemplate.from_messages([
                    ("system", "{role_instruction}"),
                    MessagesPlaceholder(variable_name="chat_history"),
                    ("user", "Here is the context retrieved from docs: {context}\nPlease answer the user's query based only on the retrieved context. User query: {user_query}")
                ])
                prompt = prompt_template.invoke({
                    "chat_history": chat_history,
                    "role_instruction": role_instruction,
                    "context": context,
                    "user_query": user_query
                })
                print("\n--- User Query ---\n")
                print(user_query)
                response = model.invoke(prompt)
                print("\n--- LLM Response ---\n")
                print(response.content)
                ai_message = response.content
                break
            else:
                print("\n--- User Query ---\n")
                print(user_query)
                print("\n--- LLM Response ---\n")
                print("Sorry, no relevant legal information could be found.")
                ai_message = "Sorry, no relevant legal information could be found."
                break

        # ✅ Summarize chat history
        if chat_history:
            summarize_prompt = (
                "Summarize the ongoing conversation by extracting concise, relevant user and AI message pairs. "
                "Format the output as a list of chat turns suitable for appending to the chat history context, ensuring continuity and coherence in future LLM responses.\n"
                + "Current chat history: "
                + str([
                    {"user": m.content} if isinstance(m, HumanMessage) else {"ai": m.content}
                    for m in chat_history
                ])
            )
            summary_response = model.invoke(summarize_prompt)
            chat_history.clear()
            chat_history.append(HumanMessage(content=summary_response.content))

        chat_history.append(HumanMessage(content=user_query))
        chat_history.append(AIMessage(content=ai_message))


if __name__ == "__main__":
    main()
