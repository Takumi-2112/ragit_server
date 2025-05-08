import os
from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from pdf_converter import convert_PDF_to_markdown
from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_EMBEDDINGS_API_KEY,
    AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
    AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME
)

# Create an AzureOpenAIEmbeddings instance
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
    api_key=AZURE_OPENAI_EMBEDDINGS_API_KEY,
    azure_deployment=AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME,
    model="text-embedding-3-small",
    openai_api_version="2024-05-01-preview"
)

# Define the path to your vector store
current_dir = os.path.dirname(os.path.abspath(__file__))

# Define the path to the folder where the vectorstore will be stored
db_folder_path = os.path.join(current_dir, "db", "chroma_vectorstore")

# Define the path to your local markdown folder
markdown_folder_path = os.path.join(current_dir, "markdown")


# Check if vectorstore exists to avoid re-indexing
if os.path.exists(db_folder_path) and os.listdir(db_folder_path):
    print("Loading existing vectorstore...")
    vectorstore = Chroma(
        persist_directory=db_folder_path,
        embedding_function=embeddings
    )
else:
    print("Creating new vectorstore...")
    
    # Define the path to your local markdown folder  
    if not os.path.exists(markdown_folder_path):
        raise ValueError(f"Markdown folder not found at {markdown_folder_path}")
      
    markdown_documents = []

    # Loop through all PDFs in the folder and convert to Markdown
    for filename in os.listdir(markdown_folder_path):
      if filename.lower().endswith(".md"):
        full_path = os.path.join(markdown_folder_path, filename)
        with open(full_path, "r", encoding="utf-8") as f:
            markdown_content = f.read()
            # Attach source metadata to each document
            markdown_documents.append(Document(
                page_content=markdown_content,
                metadata={"source": filename}
            ))

    # Split the markdown into better chunks
    text_splitter = RecursiveCharacterTextSplitter(
      chunk_size=1000,
      chunk_overlap=200,
      separators=["\n\n## ", "\n##", "\n#", "\n\n", "\n", "  ", " ", ""]
    ) 

    # Split the document
    documents = text_splitter.split_documents(markdown_documents)

    # Create a Chroma vectorstore from the markdown content
    # The vectorstore is used to store the embeddings of the text chunks
    # The embeddings are used to find similar text chunks based on the user's query
    vectorstore = Chroma.from_documents(
        documents=documents,
        embedding=embeddings,
        persist_directory=db_folder_path
    )

# Create a retriever for querying the vectorstore
# search_type specifies the type of search to perform (e.g. "similarity")
# search_kwargs specifies additional parameters for the search (e.g. number of results to return)
retriever = vectorstore.as_retriever(
    search_type="similarity",
    search_kwargs={"k": 3}
)

# Create an AzureChatOpenAI model instance
model = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-05-01-preview",
    azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
    model="gpt-4o"
)

# Contextualize question prompt
# This system prompt helps the AI understand that it should reformulate the question based on the chat history
contextualized_system_prompt = (
    "Given a chat history and the latest user question which might reference context in the chat history, "
    "formulate a standalone question which can be understood without the chat history. "
    "Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
)

# Create a prompt template for contextualizing the question
contextualize_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualized_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# Create a history aware retriever
# This will use the LLM to help reformulate the question based on the chat history
history_aware_retriever = create_history_aware_retriever(
    model, retriever, contextualize_prompt
)

# Answer the question prompt
# This system prompt helps the AI understand that it should answer the question based on the retrieved documents
qa_system_prompt = (
    "You are a professional assistant. Provide concise, professional answers "
    "based strictly on the provided context. Format responses clearly with:\n"
    "- Bullet points for lists\n"
    "- Bold text for emphasis\n"
    "- No unnecessary metadata\n"
    "If information isn't available, say so politely.\n"
    "Always maintain a professional but, good friend tone.\n\n"
    "Context:\n{context}"
)

# Create a prompt template for answering the question
qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# Create a chain to combine the documents for answering the question
# This can be done by using create_stuff_documents_chain which feeds all retrieved context to the model
question_answer_chain = create_stuff_documents_chain(model, qa_prompt)

# Create a retrieval chain that combines the history-aware retriever and the question answering chain
rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)

# Main chat loop function
def continual_chat_function():
    print("Welcome back Mr. Azran. How may I be of assistance today sir?")
    chat_history = []  # This is used to store the chat history in a sequence of messages

    # This loop will keep the chat going until the user types "exit"
    while True:
        query = input("You: ")
        if query.lower() == "exit":
            print("Goodbye Mr. Azran. Have a great day!")
            break

        # Process the user's query through the retrieval chain
        result = rag_chain.invoke({"input": query, "chat_history": chat_history})

        # Clean up the output
        clean_response = result["answer"].replace("▪", "•")  # Standardize bullet points

        # Display the AI's response
        print(f"\nAI: {clean_response}\n")  # Add spacing for readability

        # Update the chat history
        chat_history.append(HumanMessage(content=query))
        chat_history.append(SystemMessage(content=result["answer"]))

# Entry point
if __name__ == "__main__":
    continual_chat_function()
