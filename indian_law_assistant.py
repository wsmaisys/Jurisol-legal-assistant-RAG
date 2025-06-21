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
    results = vector_store.similarity_search(user_query, k=3)
    context = "\n\n".join([doc.page_content for doc in results])

    if role == "victim":
        role_instruction = (
            "You are a cunning lawyer representing the victim. "
            "Given the following context from Indian law, advise the victim on how to win the case. "
            "Provide strategies, arguments, and legal points that will help the victim succeed in court."
        )
    else:
        role_instruction = (
            "You are a cunning lawyer representing the accused. "
            "Given the following context from Indian law, advise the accused on how to be saved in court. "
            "Provide clever legal strategies, loopholes, and arguments to help the accused avoid conviction."
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
