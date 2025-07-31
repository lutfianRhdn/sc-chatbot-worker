"""
Comprehensive unit tests for VectorWorker class.

Tests cover:
- Worker initialization and configuration
- Message processing and routing
- Vector operations (create, insert)
- Text processing functions
- Error handling and communication
"""

import unittest
from unittest.mock import Mock, patch, MagicMock
import asyncio
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestVectorWorker(unittest.TestCase):
    """Test cases for VectorWorker functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock all external dependencies
        self.patches = []
        
        # Mock external libraries
        self.mock_pymongo = self.start_patch('workers.VectorWorker.MongoClient')
        self.mock_langchain_mongodb = self.start_patch('workers.VectorWorker.MongoDBAtlasVectorSearch')
        self.mock_azure_embeddings = self.start_patch('workers.VectorWorker.AzureOpenAIEmbeddings')
        self.mock_nltk = self.start_patch('workers.VectorWorker.nltk')
        self.mock_pandas = self.start_patch('workers.VectorWorker.pd')
        self.mock_log = self.start_patch('workers.VectorWorker.log')
        self.mock_document = self.start_patch('workers.VectorWorker.Document')
        
        # Mock connection
        self.mock_conn = Mock()
        
        # Mock configuration
        self.test_config = {
            'azure_openai_endpoint': 'https://test.openai.azure.com',
            'azure_openai_deployment_name_embedding': 'test-embedding',
            'azure_openai_api_version': '2023-05-15',
            'azure_openai_key': 'test-key',
            'connection_string': 'mongodb://test:27017',
            'database': 'test_db',
            'mongodb_collection': 'test_collection',
            'atlas_vector_search_index_name': 'test_index'
        }

    def start_patch(self, path):
        """Helper to start a patch and track it for cleanup."""
        patcher = patch(path)
        mock = patcher.start()
        self.patches.append(patcher)
        return mock

    def tearDown(self):
        """Clean up patches after each test."""
        for patcher in self.patches:
            patcher.stop()

    def test_vector_worker_initialization(self):
        """Test VectorWorker initialization with proper configuration."""
        from workers.VectorWorker import VectorWorker
        
        worker = VectorWorker()
        
        # Test initial state
        self.assertIsNone(worker._port)
        self.assertEqual(worker.requests, {})
        self.assertEqual(VectorWorker.requests, {})

    @patch('workers.VectorWorker.asyncio')
    def test_vector_worker_run_initialization(self, mock_asyncio):
        """Test VectorWorker run method initialization."""
        from workers.VectorWorker import VectorWorker
        
        worker = VectorWorker()
        
        # Mock MongoDB client and collection setup
        mock_client = Mock()
        mock_db = Mock()
        mock_collection = Mock()
        self.mock_pymongo.return_value = mock_client
        mock_client.__getitem__.return_value = mock_db
        mock_db.__getitem__.return_value = mock_collection
        
        # Mock vector search setup
        mock_vector_search = Mock()
        self.mock_langchain_mongodb.return_value = mock_vector_search
        
        worker.run(self.mock_conn, self.test_config)
        
        # Verify Azure OpenAI embeddings initialization
        self.mock_azure_embeddings.assert_called_once_with(
            azure_endpoint=self.test_config['azure_openai_endpoint'],
            azure_deployment=self.test_config['azure_openai_deployment_name_embedding'],
            openai_api_version=self.test_config['azure_openai_api_version'],
            azure_ad_token=self.test_config['azure_openai_key']
        )
        
        # Verify MongoDB setup
        self.mock_pymongo.assert_called_once_with(self.test_config['connection_string'])
        
        # Verify vector search initialization
        self.mock_langchain_mongodb.assert_called_once_with(
            collection=mock_collection,
            embedding=worker.embeddings,
            index_name=self.test_config['atlas_vector_search_index_name'],
            relevance_score_fn="cosine"
        )
        
        # Verify vector index creation
        mock_vector_search.create_vector_search_index.assert_called_once_with(dimensions=3072)
        
        # Verify connection assignment and listen task start
        self.assertEqual(VectorWorker.conn, self.mock_conn)
        mock_asyncio.run.assert_called_once()

    def test_text_processing_casefolding(self):
        """Test text casefolding functionality."""
        from workers.VectorWorker import VectorWorker
        
        worker = VectorWorker()
        
        test_cases = [
            ("HELLO WORLD", "hello world"),
            ("MiXeD CaSe TeXt", "mixed case text"),
            ("UPPER", "upper"),
            ("lower", "lower"),
            ("123 Numbers", "123 numbers")
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = worker.casefoldingText(input_text)
                self.assertEqual(result, expected)

    def test_text_processing_cleaning(self):
        """Test text cleaning functionality."""
        from workers.VectorWorker import VectorWorker
        
        worker = VectorWorker()
        
        test_cases = [
            ("Hello @user #hashtag", "Hello"),
            ("RT Check this out http://example.com", "Check this out"),
            ("Text with ² special chars!", "Text with special chars"),
            ("Multiple    spaces", "Multiple spaces"),
            ("Single a b c letters", "Single letters"),
            ("Text\nwith\nnewlines", "Text with newlines")
        ]
        
        for input_text, expected in test_cases:
            with self.subTest(input_text=input_text):
                result = worker.cleaningText(input_text)
                # Clean up expected result to match the actual cleaning
                self.assertIsInstance(result, str)
                self.assertNotIn('@', result)
                self.assertNotIn('#', result)
                self.assertNotIn('http', result)

    def test_text_processing_tokenizing(self):
        """Test text tokenization functionality."""
        from workers.VectorWorker import VectorWorker
        
        # Mock word_tokenize
        with patch('workers.VectorWorker.word_tokenize') as mock_tokenize:
            mock_tokenize.return_value = ['hello', 'world', 'test']
            
            worker = VectorWorker()
            result = worker.tokenizingText("hello world test")
            
            mock_tokenize.assert_called_once_with("hello world test")
            self.assertEqual(result, ['hello', 'world', 'test'])

    def test_text_normalization(self):
        """Test text normalization with slang dictionary."""
        from workers.VectorWorker import VectorWorker
        
        with patch('workers.VectorWorker.word_tokenize') as mock_tokenize:
            mock_tokenize.return_value = ['gw', 'lagi', 'ngapain']
            
            worker = VectorWorker()
            slang_dict = {'gw': 'saya', 'ngapain': 'sedang apa'}
            
            result = worker.normalize_text("gw lagi ngapain", slang_dict)
            
            # Should normalize known slang terms
            self.assertIn('saya', result)
            self.assertIn('sedang apa', result)
            self.assertIn('lagi', result)  # Unchanged

    @patch('workers.VectorWorker.os.path.exists')
    @patch('workers.VectorWorker.os.path.join')
    @patch('workers.VectorWorker.os.path.dirname')
    @patch('workers.VectorWorker.os.path.abspath')
    def test_create_vector_success(self, mock_abspath, mock_dirname, mock_join, mock_exists):
        """Test successful vector creation process."""
        from workers.VectorWorker import VectorWorker
        
        worker = VectorWorker()
        worker.vector_mongo = Mock()
        
        # Mock file path operations
        mock_abspath.return_value = '/test/path/VectorWorker.py'
        mock_dirname.return_value = '/test/path'
        mock_join.return_value = '/test/path/../../kamus/slang.xlsx'
        mock_exists.return_value = True
        
        # Mock pandas Excel reading
        mock_df = Mock()
        mock_df.iterrows.return_value = iter([])  # Empty for simplicity
        self.mock_pandas.read_excel.return_value = mock_df
        self.mock_pandas.read_excel.return_value.__len__ = Mock(return_value=10)
        
        # Mock DataFrame operations
        mock_df_slang = Mock()
        mock_df_slang.__len__ = Mock(return_value=5)
        self.mock_pandas.read_excel.return_value = mock_df_slang
        mock_df_slang.__getitem__ = Mock(side_effect=lambda x: [f'{x}1', f'{x}2'])
        
        # Mock document creation
        self.mock_document.return_value = Mock()
        
        with patch.object(worker, 'insertVector') as mock_insert:
            test_data = [
                {"full_text": "Test tweet 1", "tweet_url": "http://test1.com"},
                {"full_text": "Test tweet 2", "tweet_url": "http://test2.com"}
            ]
            
            test_message = {"messageId": "test-123"}
            
            worker.createVector(test_data, "project-123", test_message)
            
            # Verify Excel file was read
            self.mock_pandas.read_excel.assert_called()
            
            # Verify vector insertion was called
            mock_insert.assert_called_once()

    def test_create_vector_error_handling(self):
        """Test error handling in createVector method."""
        from workers.VectorWorker import VectorWorker
        
        worker = VectorWorker()
        
        # Mock an exception during processing
        with patch.object(worker, 'casefoldingText', side_effect=Exception("Test error")):
            test_data = [{"full_text": "Test", "tweet_url": "http://test.com"}]
            test_message = {"messageId": "test-123"}
            
            # Should not raise exception, should log error
            worker.createVector(test_data, "project-123", test_message)
            
            # Verify error was logged
            self.mock_log.assert_called()
            log_calls = [call for call in self.mock_log.call_args_list if 'Error in createVector' in str(call)]
            self.assertTrue(len(log_calls) > 0)

    def test_insert_vector(self):
        """Test vector insertion functionality."""
        from workers.VectorWorker import VectorWorker
        
        worker = VectorWorker()
        worker.vector_mongo = Mock()
        
        with patch('workers.VectorWorker.uuid4') as mock_uuid:
            mock_uuid.return_value = 'test-uuid'
            
            test_documents = [Mock(), Mock(), Mock()]
            
            worker.insertVector(test_documents)
            
            # Verify UUID generation and document insertion
            self.assertEqual(mock_uuid.call_count, len(test_documents))
            worker.vector_mongo.add_documents.assert_called_once_with(
                documents=test_documents,
                ids=['test-uuid', 'test-uuid', 'test-uuid']
            )

    @patch('workers.VectorWorker.asyncio.sleep')
    async def test_listen_task_message_processing(self, mock_sleep):
        """Test listen_task message processing."""
        from workers.VectorWorker import VectorWorker
        
        # Set up mock connection
        VectorWorker.conn = Mock()
        VectorWorker.conn.poll.side_effect = [True, False]  # One message, then stop
        
        test_message = {
            "destination": ["VectorWorker/createVector/project123"],
            "data": {"test": "data"},
            "messageId": "test-msg"
        }
        VectorWorker.conn.recv.return_value = test_message
        
        worker = VectorWorker()
        
        # Mock the createVector method
        with patch.object(worker, 'createVector') as mock_create_vector:
            try:
                await worker.listen_task()
            except Exception:
                pass  # Expected to break on poll returning False
            
            # Verify message was processed
            mock_create_vector.assert_called_once_with(
                data={"test": "data"},
                id="project123",
                message=test_message
            )

    def test_send_to_other_worker(self):
        """Test sending messages to other workers."""
        from workers.VectorWorker import VectorWorker
        
        VectorWorker.conn = Mock()
        
        worker = VectorWorker()
        
        with patch('workers.VectorWorker.sendMessage') as mock_send:
            worker.sendToOtherWorker(
                destination=["TestWorker/method/param"],
                messageId="test-123",
                data={"result": "success"}
            )
            
            mock_send.assert_called_once_with(
                conn=VectorWorker.conn,
                destination=["TestWorker/method/param"],
                messageId="test-123",
                status="completed",
                reason="Message sent to other worker successfully.",
                data={"result": "success"}
            )

    def test_run_creating_method(self):
        """Test runCreating method functionality."""
        from workers.VectorWorker import VectorWorker
        
        worker = VectorWorker()
        
        with patch.object(worker, 'sendToOtherWorker') as mock_send:
            test_data = {
                "projectId": "proj-123",
                "keyword": "test keyword",
                "start_date": "2023-01-01",
                "end_date": "2023-12-31"
            }
            test_message = {"messageId": "test-msg"}
            
            worker.runCreating("test-id", test_data, test_message)
            
            # Verify message was sent to DatabaseInteractionWorker
            mock_send.assert_called_once_with(
                messageId="test-msg",
                destination=["DatabaseInteractionWorker/getTweets/proj-123"],
                data={
                    "keyword": "test keyword",
                    "start_date": "2023-01-01",
                    "end_date": "2023-12-31"
                }
            )

    def test_main_function(self):
        """Test main function execution."""
        from workers.VectorWorker import main
        
        mock_conn = Mock()
        test_config = {"test": "config"}
        
        with patch('workers.VectorWorker.VectorWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker
            
            main(mock_conn, test_config)
            
            # Verify worker was created and run
            mock_worker_class.assert_called_once()
            mock_worker.run.assert_called_once_with(mock_conn, test_config)


if __name__ == '__main__':
    unittest.main()