import os
import chromadb
chromadb.telemetry.ENABLED = False

from langchain.chains import create_history_aware_retriever, create_retrieval_chain
from langchain.chains.combine_documents import create_stuff_documents_chain
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_core.messages import HumanMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_openai import AzureChatOpenAI, AzureOpenAIEmbeddings
from langchain.text_splitter import RecursiveCharacterTextSplitter
from webcrawler import webcrawl
from config import (
    AZURE_OPENAI_ENDPOINT,
    AZURE_OPENAI_DEPLOYMENT_NAME,
    AZURE_OPENAI_API_KEY,
    AZURE_OPENAI_EMBEDDINGS_API_KEY,
    AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
    AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME
)
from db.connection import get_db_connection, execute_query, close_connection
from db.queries.chats import get_all_chats_by_user_query

# Create an AzureOpenAIEmbeddings instance
embeddings = AzureOpenAIEmbeddings(
    azure_endpoint=AZURE_OPENAI_EMBEDDINGS_ENDPOINT,
    api_key=AZURE_OPENAI_EMBEDDINGS_API_KEY,
    azure_deployment=AZURE_OPENAI_EMBEDDINGS_DEPLOYMENT_NAME,
    model="text-embedding-3-small",
    openai_api_version="2024-05-01-preview"
)

# Create an AzureChatOpenAI model instance
model = AzureChatOpenAI(
    azure_endpoint=AZURE_OPENAI_ENDPOINT,
    api_key=AZURE_OPENAI_API_KEY,
    api_version="2024-05-01-preview",
    azure_deployment=AZURE_OPENAI_DEPLOYMENT_NAME,
    model="gpt-4o"
)

# Store chat histories per user (in-memory cache)
user_chat_histories = {}

# Contextualize question prompt
contextualized_system_prompt = (
    "Given a chat history and the latest user question which might reference context in the chat history, "
    "formulate a standalone question which can be understood without the chat history. "
    "Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
)

contextualize_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", contextualized_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

# Answer the question prompt
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

qa_prompt = ChatPromptTemplate.from_messages(
    [
        ("system", qa_system_prompt),
        MessagesPlaceholder("chat_history"),
        ("human", "{input}"),
    ]
)

def get_user_vectorstore(user_id):
    """
    Get or create a user-specific vectorstore
    """
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_folder_path = os.path.join(current_dir, "db", "vectorstores", f"user_{user_id}_vectorstore")
    
    # Ensure the directory exists
    os.makedirs(db_folder_path, exist_ok=True)
    
    # Check if vectorstore already exists
    if os.path.exists(db_folder_path) and os.listdir(db_folder_path):
        print(f"Loading existing vectorstore for user {user_id}...")
        vectorstore = Chroma(
            persist_directory=db_folder_path,
            embedding_function=embeddings
        )
    else:
        print(f"Creating new vectorstore for user {user_id}...")
        # Create empty vectorstore
        vectorstore = Chroma(
            persist_directory=db_folder_path,
            embedding_function=embeddings
        )
        
        # Check for markdown files in the general markdown folder to initialize with
        markdown_folder_path = os.path.join(current_dir, "markdown")
        if os.path.exists(markdown_folder_path):
            markdown_documents = []
            for filename in os.listdir(markdown_folder_path):
                if filename.lower().endswith(".md"):
                    full_path = os.path.join(markdown_folder_path, filename)
                    with open(full_path, "r", encoding="utf-8") as f:
                        content = f.read().strip()
                        if content:
                            markdown_documents.append(Document(
                                page_content=content,
                                metadata={"source": filename}
                            ))
            
            # Add markdown documents to the new user's vectorstore if any exist
            if markdown_documents:
                print(f"Initializing user {user_id} vectorstore with {len(markdown_documents)} markdown files...")
                text_splitter = RecursiveCharacterTextSplitter(
                    chunk_size=1000,
                    chunk_overlap=200,
                    separators=["\n\n## ", "\n##", "\n#", "\n\n", "\n", "  ", " ", ""]
                )
                documents = text_splitter.split_documents(markdown_documents)
                vectorstore.add_documents(documents)
    
    return vectorstore

def get_user_chat_history_from_db(user_id):
    """
    Get chat history for a specific user from the database and convert to LangChain format
    """
    try:
        query = get_all_chats_by_user_query()
        messages = execute_query(query, params=(user_id,), fetch_all=True)
        
        # Convert to LangChain message format
        chat_history = []
        if messages:
            for msg in messages:
                if msg['sender'] == 'user':
                    chat_history.append(HumanMessage(content=msg['message_text']))
                else:
                    chat_history.append(SystemMessage(content=msg['message_text']))
        
        return chat_history
    except Exception as e:
        print(f"Error retrieving chat history from DB: {str(e)}")
        return []

def get_user_chat_history(user_id):
    """
    Get or create chat history for a specific user from database cache
    """
    if user_id not in user_chat_histories:
        # Load from database
        user_chat_histories[user_id] = get_user_chat_history_from_db(user_id)
    return user_chat_histories[user_id]

def update_user_chat_history_cache(user_id, human_message, system_message):
    """
    Update the in-memory chat history cache
    """
    if user_id not in user_chat_histories:
        user_chat_histories[user_id] = []
    
    user_chat_histories[user_id].append(HumanMessage(content=human_message))
    user_chat_histories[user_id].append(SystemMessage(content=system_message))

def create_rag_chain_for_user(user_id):
    """
    Create a RAG chain for a specific user
    """
    vectorstore = get_user_vectorstore(user_id)
    
    retriever = vectorstore.as_retriever(
        search_type="similarity",
        search_kwargs={"k": 3}
    )
    
    history_aware_retriever = create_history_aware_retriever(
        model, retriever, contextualize_prompt
    )
    
    question_answer_chain = create_stuff_documents_chain(model, qa_prompt)
    
    rag_chain = create_retrieval_chain(history_aware_retriever, question_answer_chain)
    
    return rag_chain

def url_to_vectorstore(url, user_id):
    """
    Add URL content to a user-specific vectorstore
    """
    content = webcrawl(url)
    
    if not content:
        print(f"Failed to retrieve content from {url}")
        return False
    
    # Get the user's vectorstore
    vectorstore = get_user_vectorstore(user_id)
    
    # Wrap the content in the langchain document format
    document = Document(
        page_content=content,
        metadata={"source": url}
    )
    
    # Split the document into chunks
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["\n\n", "\n", " ", ""]
    )
    
    split_docs = text_splitter.split_documents([document])
    
    # Add the chunks to the user's vectorstore
    vectorstore.add_documents(split_docs)
    
    print(f"Successfully added content from {url} to user {user_id}'s vectorstore.")
    return True

def chatbot_talk(prompt, user_id):
    """
    Process a chat message for a specific user
    """
    # Get the user's chat history from cache/database
    chat_history = get_user_chat_history(user_id)
    
    # Create RAG chain for this user
    rag_chain = create_rag_chain_for_user(user_id)
    
    # Process the user's prompt through the retrieval chain
    result = rag_chain.invoke({"input": prompt, "chat_history": chat_history})

    # Clean up the output
    clean_response = result["answer"].replace("▪", "•")

    # Display the AI's response (for debugging)
    print(f"\nAI response for user {user_id}: {clean_response}\n")

    # Update the user's chat history cache
    # Note: The actual database saving is handled in server.py
    update_user_chat_history_cache(user_id, prompt, result["answer"])
    
    return clean_response

def clear_user_chat_history_cache(user_id):
    """
    Clear the in-memory chat history cache for a user
    """
    if user_id in user_chat_histories:
        user_chat_histories[user_id] = []

# Export functions for use in server.py
__all__ = ['chatbot_talk', 'url_to_vectorstore', 'get_user_vectorstore', 'clear_user_chat_history_cache']

# Entry point for standalone usage
if __name__ == "__main__":
    # For testing purposes, use default user
    test_user_id = "default"
    
    print(f"Welcome! Testing RAG system for user {test_user_id}")
    
    while True:
        query = input("You: ")
        if query.lower() == "exit":
            print("Goodbye!")
            break
        
        response = chatbot_talk(query, test_user_id)
        print(f"AI: {response}")