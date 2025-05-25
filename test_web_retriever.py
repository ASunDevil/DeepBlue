import asyncio
import unittest
from unittest.mock import patch, AsyncMock, MagicMock 

# Assuming web_retriever.py is in the same directory or accessible via PYTHONPATH
try:
    from web_retriever import get_web_content, create_vector_store_from_url
    # Specific LangChain component imports for type hinting and mocking if necessary
    from langchain_community.vectorstores import FAISS as LangchainFAISS 
    from langchain_core.documents import Document
    from langchain_openai.embeddings import OpenAIEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter
except ImportError:
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.abspath(__file__)))
    from web_retriever import get_web_content, create_vector_store_from_url
    from langchain_community.vectorstores import FAISS as LangchainFAISS
    from langchain_core.documents import Document
    from langchain_openai.embeddings import OpenAIEmbeddings
    from langchain.text_splitter import RecursiveCharacterTextSplitter


# A known public URL for testing that is simple and stable
VALID_URL_EXAMPLE_COM = "http://example.com/" 
VALID_URL_GOOGLE = "https://www.google.com/" 

NON_EXISTENT_DOMAIN_URL = "http://thishouldnotbearealdomain12345abcxyz.com/"

EMPTY_CONTENT_DATA_URI = "data:text/html,"
MINIMAL_HTML_DATA_URI = "data:text/html,<html><head><title>Test</title></head><body></body></html>"


class TestGetWebContent(unittest.IsolatedAsyncioTestCase):

    async def test_valid_url_example_com(self):
        print(f"\nRunning: test_valid_url_example_com with URL: {VALID_URL_EXAMPLE_COM}")
        content = await get_web_content(VALID_URL_EXAMPLE_COM)
        self.assertIsInstance(content, str)
        self.assertTrue(len(content) > 0, "Content should not be empty for example.com")
        self.assertIn("<html", content.lower(), "HTML tag not found in content from example.com")
        self.assertIn("example domain", content.lower(), "Expected text 'example domain' not found in content")
        # print(f"Content received (first 100 chars): {content[:100]}") # Keep for debugging if needed

    async def test_valid_url_google_com(self):
        print(f"\nRunning: test_valid_url_google_com with URL: {VALID_URL_GOOGLE}")
        content = await get_web_content(VALID_URL_GOOGLE)
        self.assertIsInstance(content, str)
        self.assertTrue(len(content) > 0, "Content should not be empty for google.com")
        self.assertIn("<html", content.lower(), "HTML tag not found in content from google.com")
        # print(f"Content received (first 100 chars): {content[:100]}")

    async def test_invalid_url_scheme_ftp(self):
        print("\nRunning: test_invalid_url_scheme_ftp")
        url = "ftp://example.com"
        content = await get_web_content(url)
        self.assertEqual(content, "Error: Invalid URL scheme. URL must start with 'http://' or 'https://'.")

    async def test_invalid_url_scheme_no_scheme(self):
        print("\nRunning: test_invalid_url_scheme_no_scheme")
        url = "example.com"
        content = await get_web_content(url)
        self.assertEqual(content, "Error: Invalid URL scheme. URL must start with 'http://' or 'https://'.")

    async def test_non_string_url_integer(self):
        print("\nRunning: test_non_string_url_integer")
        url = 123
        content = await get_web_content(url) # type: ignore 
        self.assertEqual(content, "Error: URL must be a string.")

    async def test_non_string_url_list(self):
        print("\nRunning: test_non_string_url_list")
        url = ["http://example.com"]
        content = await get_web_content(url) # type: ignore
        self.assertEqual(content, "Error: URL must be a string.")

    async def test_network_error_non_existent_domain(self):
        print(f"\nRunning: test_network_error_non_existent_domain with URL: {NON_EXISTENT_DOMAIN_URL}")
        content = await get_web_content(NON_EXISTENT_DOMAIN_URL)
        self.assertTrue(content.startswith(f"Error: Could not retrieve content from URL: {NON_EXISTENT_DOMAIN_URL}."), 
                        f"Unexpected error message: {content}")
        # print(f"Error message received: {content}")

    async def test_empty_content_data_uri_empty(self):
        print(f"\nRunning: test_empty_content_data_uri_empty with URL: {EMPTY_CONTENT_DATA_URI}")
        content = await get_web_content(EMPTY_CONTENT_DATA_URI)
        expected_minimal_html = "<html><head></head><body></body></html>"
        if content == expected_minimal_html or content == "":
             pass 
        else:
            self.assertTrue(content.startswith("Error: No content found at the URL"),
                            f"Expected minimal HTML or 'No content found' error, but got: '{content}'")
        # print(f"Content from empty data URI: '{content}'")

    async def test_empty_content_data_uri_minimal_html(self):
        print(f"\nRunning: test_empty_content_data_uri_minimal_html with URL: {MINIMAL_HTML_DATA_URI}")
        content = await get_web_content(MINIMAL_HTML_DATA_URI)
        self.assertEqual(content, "<html><head><title>Test</title></head><body></body></html>")
        # print(f"Content from minimal HTML data URI: '{content}'")


class TestCreateVectorStoreFromURL(unittest.IsolatedAsyncioTestCase):

    DUMMY_URL = "http://dummyurl.com"
    DUMMY_API_KEY = "sk-fakekey123"
    MOCK_HTML_CONTENT = "<html><body>Mocked web content. This is a test page. It has some text.</body></html>"
    MOCK_ERROR_HTML_CONTENT_RETRIEVAL = "Error: Could not retrieve content from URL."

    @patch('web_retriever.FAISS.afrom_documents', new_callable=AsyncMock)
    @patch('web_retriever.OpenAIEmbeddings') # Patch the class
    @patch('web_retriever.RecursiveCharacterTextSplitter.acreate_documents', new_callable=AsyncMock)
    @patch('web_retriever.get_web_content', new_callable=AsyncMock)
    async def test_successful_vector_store_creation(
        self, 
        mock_get_web_content, 
        mock_acreate_documents,
        mock_openai_embeddings_class, 
        mock_faiss_afrom_documents
    ):
        print("\nRunning: test_successful_vector_store_creation")
        # --- Setup Mocks ---
        mock_get_web_content.return_value = self.MOCK_HTML_CONTENT
        
        # Mock RecursiveCharacterTextSplitter().acreate_documents()
        mock_split_docs = [Document(page_content="Mocked web content.", metadata={"start_index": 0}), 
                           Document(page_content="This is a test page.", metadata={"start_index": 20}),
                           Document(page_content="It has some text.", metadata={"start_index": 40})]
        mock_acreate_documents.return_value = mock_split_docs

        # Mock OpenAIEmbeddings instance
        mock_embeddings_instance = MagicMock(spec=OpenAIEmbeddings)
        mock_openai_embeddings_class.return_value = mock_embeddings_instance

        # Mock FAISS.afrom_documents to return a mock FAISS store
        mock_faiss_store_instance = AsyncMock(spec=LangchainFAISS)
        mock_faiss_store_instance.asimilarity_search = AsyncMock(return_value=[Document(page_content="Mocked web content.")])
        mock_faiss_afrom_documents.return_value = mock_faiss_store_instance

        # --- Call the function ---
        vector_store = await create_vector_store_from_url(self.DUMMY_URL, self.DUMMY_API_KEY)

        # --- Assertions ---
        self.assertIsNotNone(vector_store, "Vector store should not be None on success.")
        self.assertEqual(vector_store, mock_faiss_store_instance, "Returned object is not the mocked FAISS store.")

        mock_get_web_content.assert_called_once_with(self.DUMMY_URL)
        
        # Assert RecursiveCharacterTextSplitter was initialized and used
        # Harder to assert constructor directly, but acreate_documents call implies it was.
        mock_acreate_documents.assert_called_once_with([self.MOCK_HTML_CONTENT])
        
        mock_openai_embeddings_class.assert_called_once_with(openai_api_key=self.DUMMY_API_KEY)
        mock_faiss_afrom_documents.assert_called_once_with(mock_split_docs, mock_embeddings_instance)
        
        # Test similarity search on the returned (mocked) store
        query = "What is this page about?"
        search_results = await vector_store.asimilarity_search(query, k=1) # type: ignore
        self.assertIsNotNone(search_results)
        self.assertTrue(len(search_results) > 0)
        self.assertEqual(search_results[0].page_content, "Mocked web content.")
        mock_faiss_store_instance.asimilarity_search.assert_called_once_with(query, k=1)
        print("Successful vector store creation test passed.")

    @patch('web_retriever.get_web_content', new_callable=AsyncMock)
    async def test_get_web_content_returns_error_string(self, mock_get_web_content):
        print("\nRunning: test_get_web_content_returns_error_string")
        mock_get_web_content.return_value = self.MOCK_ERROR_HTML_CONTENT_RETRIEVAL
        
        with patch('web_retriever.OpenAIEmbeddings') as mock_embeddings, \
             patch('web_retriever.FAISS.afrom_documents') as mock_faiss:
            vector_store = await create_vector_store_from_url(self.DUMMY_URL, self.DUMMY_API_KEY)
            
            self.assertIsNone(vector_store, "Vector store should be None if get_web_content fails.")
            mock_get_web_content.assert_called_once_with(self.DUMMY_URL)
            mock_embeddings.assert_not_called()
            mock_faiss.assert_not_called()
        print("get_web_content error string test passed.")

    @patch('web_retriever.get_web_content', new_callable=AsyncMock)
    async def test_get_web_content_returns_empty_string(self, mock_get_web_content):
        print("\nRunning: test_get_web_content_returns_empty_string")
        mock_get_web_content.return_value = "" # Empty string
        
        with patch('web_retriever.RecursiveCharacterTextSplitter.acreate_documents') as mock_splitter, \
             patch('web_retriever.OpenAIEmbeddings') as mock_embeddings, \
             patch('web_retriever.FAISS.afrom_documents') as mock_faiss:
            vector_store = await create_vector_store_from_url(self.DUMMY_URL, self.DUMMY_API_KEY)
            
            self.assertIsNone(vector_store, "Vector store should be None for empty content.")
            mock_get_web_content.assert_called_once_with(self.DUMMY_URL)
            mock_splitter.assert_not_called() # Should exit before splitting
            mock_embeddings.assert_not_called()
            mock_faiss.assert_not_called()
        print("Empty web content test passed.")

    @patch('web_retriever.get_web_content', new_callable=AsyncMock)
    async def test_get_web_content_returns_whitespace_string(self, mock_get_web_content):
        print("\nRunning: test_get_web_content_returns_whitespace_string")
        mock_get_web_content.return_value = "   \n\t   " # Whitespace only
        
        with patch('web_retriever.RecursiveCharacterTextSplitter.acreate_documents') as mock_splitter, \
             patch('web_retriever.OpenAIEmbeddings') as mock_embeddings, \
             patch('web_retriever.FAISS.afrom_documents') as mock_faiss:
            vector_store = await create_vector_store_from_url(self.DUMMY_URL, self.DUMMY_API_KEY)
            
            self.assertIsNone(vector_store, "Vector store should be None for whitespace content.")
            mock_get_web_content.assert_called_once_with(self.DUMMY_URL)
            mock_splitter.assert_not_called() # Should exit before splitting
            mock_embeddings.assert_not_called()
            mock_faiss.assert_not_called()
        print("Whitespace web content test passed.")

    @patch('web_retriever.get_web_content', new_callable=AsyncMock)
    @patch('web_retriever.RecursiveCharacterTextSplitter.acreate_documents', new_callable=AsyncMock)
    async def test_text_splitting_yields_no_documents(self, mock_acreate_documents, mock_get_web_content):
        print("\nRunning: test_text_splitting_yields_no_documents")
        mock_get_web_content.return_value = self.MOCK_HTML_CONTENT
        mock_acreate_documents.return_value = [] # Text splitter returns no docs
        
        with patch('web_retriever.OpenAIEmbeddings') as mock_embeddings, \
             patch('web_retriever.FAISS.afrom_documents') as mock_faiss:
            vector_store = await create_vector_store_from_url(self.DUMMY_URL, self.DUMMY_API_KEY)
            
            self.assertIsNone(vector_store, "Vector store should be None if splitting yields no documents.")
            mock_get_web_content.assert_called_once_with(self.DUMMY_URL)
            mock_acreate_documents.assert_called_once()
            mock_embeddings.assert_not_called() # Should not proceed to embeddings
            mock_faiss.assert_not_called()
        print("No documents after text splitting test passed.")

    @patch('web_retriever.get_web_content', new_callable=AsyncMock)
    @patch('web_retriever.RecursiveCharacterTextSplitter.acreate_documents', new_callable=AsyncMock)
    @patch('web_retriever.OpenAIEmbeddings', side_effect=ValueError("Mocked OpenAI API Key Error"))
    async def test_openai_embeddings_initialization_raises_exception(
        self, 
        mock_openai_embeddings_class_with_error, 
        mock_acreate_documents,
        mock_get_web_content
    ):
        print("\nRunning: test_openai_embeddings_initialization_raises_exception")
        mock_get_web_content.return_value = self.MOCK_HTML_CONTENT
        mock_acreate_documents.return_value = [Document(page_content="doc1")] # Assume splitting works

        with patch('web_retriever.FAISS.afrom_documents') as mock_faiss:
            vector_store = await create_vector_store_from_url(self.DUMMY_URL, self.DUMMY_API_KEY)
            
            self.assertIsNone(vector_store, "Vector store should be None if OpenAIEmbeddings init fails.")
            mock_get_web_content.assert_called_once()
            mock_acreate_documents.assert_called_once()
            mock_openai_embeddings_class_with_error.assert_called_once_with(openai_api_key=self.DUMMY_API_KEY)
            mock_faiss.assert_not_called()
        print("OpenAIEmbeddings initialization failure test passed.")

    @patch('web_retriever.get_web_content', new_callable=AsyncMock)
    @patch('web_retriever.RecursiveCharacterTextSplitter.acreate_documents', new_callable=AsyncMock)
    @patch('web_retriever.OpenAIEmbeddings')
    @patch('web_retriever.FAISS.afrom_documents', new_callable=AsyncMock, side_effect=Exception("Mocked FAISS Creation Error"))
    async def test_faiss_afrom_documents_raises_exception(
        self, 
        mock_faiss_afrom_documents_with_error, 
        mock_openai_embeddings_class,
        mock_acreate_documents, 
        mock_get_web_content
    ):
        print("\nRunning: test_faiss_afrom_documents_raises_exception")
        mock_get_web_content.return_value = self.MOCK_HTML_CONTENT
        mock_acreate_documents.return_value = [Document(page_content="doc1")]
        
        mock_embeddings_instance = MagicMock(spec=OpenAIEmbeddings)
        mock_openai_embeddings_class.return_value = mock_embeddings_instance

        vector_store = await create_vector_store_from_url(self.DUMMY_URL, self.DUMMY_API_KEY)
        
        self.assertIsNone(vector_store, "Vector store should be None if FAISS.afrom_documents fails.")
        mock_get_web_content.assert_called_once()
        mock_acreate_documents.assert_called_once()
        mock_openai_embeddings_class.assert_called_once_with(openai_api_key=self.DUMMY_API_KEY)
        mock_faiss_afrom_documents_with_error.assert_called_once_with(
            [Document(page_content="doc1")], 
            mock_embeddings_instance
        )
        print("FAISS.afrom_documents failure test passed.")


if __name__ == '__main__':
    unittest.main()
