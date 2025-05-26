import asyncio
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter # For splitting text
from langchain_openai.embeddings import OpenAIEmbeddings # For OpenAI embeddings
from langchain_community.vectorstores import FAISS # For FAISS vector store
from datetime import datetime
import traceback

async def get_web_content(url: str) -> str:
    """
    Asynchronously loads content from a given URL using WebBaseLoader.

    Args:
        url: The URL to fetch content from.

    Returns:
        A string containing the concatenated page content of all loaded documents,
        or an error message if fetching fails.
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] Entering get_web_content with url='{url}'")
    if not isinstance(url, str):
        error_string = "Error: URL must be a string."
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting get_web_content (validation failed) with error: '{error_string}'")
        return error_string
    if not url.startswith(('http://', 'https://')):
        error_string = "Error: Invalid URL scheme. URL must start with 'http://' or 'https://'."
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting get_web_content (validation failed) with error: '{error_string}'")
        return error_string

    loader = WebBaseLoader(url)
    print(f"DEBUG: [%{datetime.now().isoformat()}] WebBaseLoader initialized for {url}")
    all_page_content = []
    try:
        async for doc in loader.alazy_load():
            if isinstance(doc, Document) and hasattr(doc, 'page_content'):
                all_page_content.append(doc.page_content)
            else:
                # Handle cases where the item might not be a Document or lacks page_content
                print(f"DEBUG: [%{datetime.now().isoformat()}] Warning: Encountered an unexpected item in loader: {doc}") 
        
        print(f"DEBUG: [%{datetime.now().isoformat()}] Loaded {len(all_page_content)} document parts from {url}")
        if not all_page_content:
            error_string = "Error: No content found at the URL or content could not be processed."
            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting get_web_content (no content) with error: '{error_string}'")
            return error_string

        content_string = "".join(all_page_content)
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting get_web_content successfully. Content length: {len(content_string)}. Preview: '{content_string[:100]}...'")
        return content_string
    except Exception as e:
        formatted_traceback = traceback.format_exc()
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exception in get_web_content for {url}: {e}\nTraceback:\n{formatted_traceback}")
        error_string = f"Error: Could not retrieve content from URL: {url}. Details: {e}"
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting get_web_content (exception) with error: '{error_string}'")
        return error_string

async def create_vector_store_from_url(url: str, openai_api_key: str) -> FAISS | None:
    """
    Creates a FAISS vector store from the content of a given URL.

    It fetches the web content, splits it into manageable chunks,
    generates embeddings using OpenAI, and stores them in a FAISS index.

    Args:
        url: The URL to fetch content from.
        openai_api_key: The OpenAI API key for generating embeddings.
                        If None, OpenAIEmbeddings will try to use the
                        OPENAI_API_KEY environment variable.

    Returns:
        A FAISS vector store instance if successful, otherwise None.
    """
    print(f"DEBUG: [%{datetime.now().isoformat()}] Starting vector store creation for URL: {url}")
    print(f"DEBUG: [%{datetime.now().isoformat()}] create_vector_store_from_url called with url='{url}', openai_api_key='{'*' * (len(openai_api_key) - 4) + openai_api_key[-4:] if openai_api_key and len(openai_api_key) > 4 else 'Not provided or too short'}'")

    # 1. Get raw text content from the URL
    raw_text_content = await get_web_content(url)
    print(f"DEBUG: [%{datetime.now().isoformat()}] get_web_content returned. Length: {len(raw_text_content)}. Preview: {raw_text_content[:100] if not raw_text_content.startswith('Error:') else raw_text_content}")
    if raw_text_content.startswith("Error:"):
        print(f"DEBUG: [%{datetime.now().isoformat()}] Failed to get content from URL: {url}. Error: {raw_text_content}")
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting create_vector_store_from_url (failed to get content) returning None. Error: {raw_text_content}")
        return None

    if not raw_text_content.strip():
        print(f"DEBUG: [%{datetime.now().isoformat()}] No actual text content found at URL: {url} after stripping whitespace.")
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting create_vector_store_from_url (no actual text content) returning None.")
        return None
        
    print(f"DEBUG: [%{datetime.now().isoformat()}] Successfully fetched content from URL (first 200 chars): {raw_text_content[:200]}")

    try:
        # 2. Initialize RecursiveCharacterTextSplitter
        # add_start_index can be helpful for locating the source of chunks.
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200,
            add_start_index=True
        )
        print(f"DEBUG: [%{datetime.now().isoformat()}] Initialized RecursiveCharacterTextSplitter with chunk_size={text_splitter.chunk_size}, chunk_overlap={text_splitter.chunk_overlap}")

        # 3. Split the text into document chunks
        # create_documents expects a list of texts. We have one large text.
        # It will create Document objects for each chunk.
        print(f"DEBUG: [%{datetime.now().isoformat()}] Splitting document into chunks...")
        split_docs = await text_splitter.acreate_documents([raw_text_content])
        
        if not split_docs:
            print(f"DEBUG: [%{datetime.now().isoformat()}] Text splitting resulted in no documents. Cannot create vector store.")
            print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting create_vector_store_from_url (no documents after split) returning None.")
            return None
        print(f"DEBUG: [%{datetime.now().isoformat()}] Document split into {len(split_docs)} chunks.")

        # 4. Initialize OpenAIEmbeddings
        print(f"DEBUG: [%{datetime.now().isoformat()}] Initializing OpenAI embeddings model...")
        embeddings_model = OpenAIEmbeddings(openai_api_key=openai_api_key)
        print(f"DEBUG: [%{datetime.now().isoformat()}] OpenAIEmbeddings model initialized.")

        # 5. Create FAISS vector store
        print(f"DEBUG: [%{datetime.now().isoformat()}] Creating FAISS vector store from documents and embeddings...")
        # FAISS.afrom_documents is the asynchronous method to create the store
        vector_store = await FAISS.afrom_documents(split_docs, embeddings_model)
        print(f"DEBUG: [%{datetime.now().isoformat()}] FAISS vector store created successfully.")
        
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting create_vector_store_from_url successfully. Returning FAISS vector store instance.")
        return vector_store

    except Exception as e:
        # Log the full exception for debugging if necessary (already present)
        print(f"DEBUG: [%{datetime.now().isoformat()}] An error occurred during vector store creation for URL {url}: {e}")
        traceback.print_exc() 
        print(f"DEBUG: [%{datetime.now().isoformat()}] Exiting create_vector_store_from_url (exception during creation) returning None.")
        return None

# Example of how to run these async functions (optional, for testing)
# if __name__ == '__main__':
#     async def main():
#         test_url = "https://example.com" # A simple, stable URL
#         # IMPORTANT: Set your OpenAI API key as an environment variable:
#         # export OPENAI_API_KEY="your_actual_api_key"
#         # Or, pass it directly (less secure for shared code):
#         api_key = os.environ.get("OPENAI_API_KEY") 
#
#         if not api_key:
#             print("OPENAI_API_KEY environment variable not set. Skipping create_vector_store_from_url test.")
#             return
#
#         print(f"\nAttempting to create vector store for: {test_url}")
#         vector_store_instance = await create_vector_store_from_url(test_url, api_key)
#
#         if vector_store_instance:
#             print(f"\nSuccessfully created vector store for {test_url}.")
#             # You can try a similarity search if you have a query
#             try:
#                 query = "What is this page about?"
#                 search_results = await vector_store_instance.asimilarity_search(query, k=2)
#                 print(f"\nSimilarity search results for query: '{query}'")
#                 for i, doc in enumerate(search_results):
#                     print(f"Result {i+1}:")
#                     print(f"  Page Content (first 100 chars): {doc.page_content[:100]}...")
#                     print(f"  Metadata: {doc.metadata}")
#             except Exception as e:
#                 print(f"Error during similarity search: {e}")
#         else:
#             print(f"\nFailed to create vector store for {test_url}.")
#
#     # You would need to set the OPENAI_API_KEY environment variable for the example to run.
#     # import os # Make sure to import os if you use os.environ.get()
#     # asyncio.run(main())
