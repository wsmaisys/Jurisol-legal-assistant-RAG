from langchain_chroma import Chroma
from langchain_mistralai import MistralAIEmbeddings, ChatMistralAI
from langchain_core.prompts import PromptTemplate
from dotenv import load_dotenv

load_dotenv()

# Load the vector store
vector_store = Chroma(
    embedding_function=MistralAIEmbeddings(model="mistral-embed"),
    persist_directory='./indian_law_vector_store',
    collection_name='indian_law_docs'
)

def main():
    print("Do you want the lawyer to aid the victim or the accused?")
    while True:
        role = input("Type 'victim' or 'accused': ").strip().lower()
        if role in ("victim", "accused"):
            break
        print("Please type 'victim' or 'accused'.")

    user_query = input("Enter your legal query: ")

    print(f"\nSearching vector store for relevant context...\n")
    results = vector_store.similarity_search_with_score(user_query, k=8)
    context = "\n\n".join([doc.page_content for doc in results])

    if role == "victim":
        role_instruction = (
            "You are a legal assistant strictly limited to the provided legal context extracted from Indian law. "
            "Do not use any external knowledge or assumptions beyond the context given. "
            "Your role is to support the victim’s side based solely on the embedded context supplied. "
            "Advise the victim on what will be the legal procedures to be followed now, "
            "including the possible legal actions, rights, and remedies available, along with any relevant sections of the law, "
            "but only if such guidance is explicitly supported by the context. "
            "If the context is insufficient to answer, respond with: "
            "'My current legal knowledge does not contain sufficient information to advise on this matter.' "
            "Do not speculate or answer beyond the context under any circumstance."
        )
    else:
        role_instruction = (
            "You are a legal assistant strictly limited to the provided legal context extracted from Indian law. "
            "Do not use any external knowledge or assumptions beyond the context given. "
            "Your role is to support the accused’s side based solely on the embedded context supplied. "
            "Advise the accused on what will be the legal procedures to be followed now, "
            "including the possible legal defenses, rights, and loopholes available, along with any relevant sections of the law, "
            "but only if such guidance is explicitly supported by the context. "
            "If the context is insufficient to answer, respond with: "
            "'My current legal knowledge does not contain sufficient information to advise on this matter.' "
            "Do not speculate or answer beyond the context under any circumstance."
        )


    template = PromptTemplate(
        template=(
            "{role_instruction}\n"
            "Context from Indian law:\n{context}\n\n"
            "User Query: {query}\n"
            "Respond as a legal expert, citing relevant sections if possible."
        ),
        input_variables=["role_instruction", "context", "query"]
    )

    prompt = template.format(role_instruction=role_instruction, context=context, query=user_query)
    model = ChatMistralAI(model="mistral-small-latest", temperature=0.1)
    print("\nGenerating answer using LLM...\n")
    result = model.invoke(prompt)
    print("\n--- Answer ---\n")
    print(result.content)

if __name__ == "__main__":
    main()
