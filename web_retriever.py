import asyncio
from langchain_community.document_loaders import WebBaseLoader
from langchain_core.documents import Document

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
                # This could be logged or handled as a less critical error
                print(f"Warning: Encountered an unexpected item in loader: {doc}") # Or log this
        
        if not all_page_content:
            return "Error: No content found at the URL or content could not be processed."

        return "".join(all_page_content)
    except Exception as e:
        return f"Error: Could not retrieve content from URL: {url}. Details: {e}"

# Example of how to run this async function (optional, for testing)
# if __name__ == '__main__':
#     async def main():
#         # Test with a valid URL
#         content = await get_web_content("https://www.google.com")
#         print("Content from google.com:")
#         print(content[:500]) # Print first 500 chars
#
#         # Test with an invalid URL
#         error_content = await get_web_content("not_a_real_url")
#         print("\nContent from invalid URL:")
#         print(error_content)
#
#         # Test with a URL that might cause a network error (e.g., a non-existent domain)
#         network_error_content = await get_web_content("http://thisdomainprobablydoesnotexist12345.com")
#         print("\nContent from non-existent domain:")
#         print(network_error_content)
#
#     asyncio.run(main())
