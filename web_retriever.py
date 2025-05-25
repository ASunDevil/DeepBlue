import asyncio
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter # For splitting text
from langchain_openai.embeddings import OpenAIEmbeddings # For OpenAI embeddings
from langchain_community.vectorstores import FAISS # For FAISS vector store

async def get_web_content(url: str) -> str:
    """
    Asynchronously loads content from a given URL using WebBaseLoader.

    Args:
        url: The URL to fetch content from.

    Returns:
        A string containing the concatenated page content of all loaded documents,
        or an error message if fetching fails.
    """
    if not isinstance(url, str):
        return "Error: URL must be a string."
    if not url.startswith(('http://', 'https://')):
        return "Error: Invalid URL scheme. URL must start with 'http://' or 'https://'."

    loader = WebBaseLoader(url)
    all_page_content = []
    try:
        async for doc in loader.alazy_load():
            if isinstance(doc, Document) and hasattr(doc, 'page_content'):
                all_page_content.append(doc.page_content)
            else:
                # Handle cases where the item might not be a Document or lacks page_content
                print(f"Warning: Encountered an unexpected item in loader: {doc}") 
        
        if not all_page_content:
            return "Error: No content found at the URL or content could not be processed."

        return "".join(all_page_content)
    except Exception as e:
        return f"Error: Could not retrieve content from URL: {url}. Details: {e}"

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
    print(f"Starting vector store creation for URL: {url}")

    # 1. Get raw text content from the URL
    raw_text_content = await get_web_content(url)
    if raw_text_content.startswith("Error:"):
        print(f"Failed to get content from URL: {url}. Error: {raw_text_content}")
        return None

    if not raw_text_content.strip():
        print(f"No actual text content found at URL: {url} after stripping whitespace.")
        return None
        
    print(f"Successfully fetched content from URL (first 200 chars): {raw_text_content[:200]}")

    try:
        # 2. Initialize RecursiveCharacterTextSplitter
        # add_start_index can be helpful for locating the source of chunks.
        text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000, 
            chunk_overlap=200,
            add_start_index=True
        )

        # 3. Split the text into document chunks
        # create_documents expects a list of texts. We have one large text.
        # It will create Document objects for each chunk.
        print("Splitting document into chunks...")
        split_docs = await text_splitter.acreate_documents([raw_text_content])
        
        if not split_docs:
            print("Text splitting resulted in no documents. Cannot create vector store.")
            return None
        print(f"Document split into {len(split_docs)} chunks.")

        # 4. Initialize OpenAIEmbeddings
        print("Initializing OpenAI embeddings model...")
        embeddings_model = OpenAIEmbeddings(openai_api_key=openai_api_key)

        # 5. Create FAISS vector store
        print("Creating FAISS vector store from documents and embeddings...")
        # FAISS.afrom_documents is the asynchronous method to create the store
        vector_store = await FAISS.afrom_documents(split_docs, embeddings_model)
        print("FAISS vector store created successfully.")
        
        return vector_store

    except Exception as e:
        print(f"An error occurred during vector store creation for URL {url}: {e}")
        # Log the full exception for debugging if necessary
        import traceback
        traceback.print_exc()
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
