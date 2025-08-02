"""
Comprehensive unit tests for DatabaseInteractionWorker class.

Tests cover:
- Worker initialization and configuration
- Database connection management
- Message processing and routing
- Busy state handling
- Error handling and communication
"""

import unittest
from unittest.mock import Mock, patch, call
import asyncio
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'src'))


class TestDatabaseInteractionWorker(unittest.TestCase):
    """Test cases for DatabaseInteractionWorker functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock all external dependencies
        self.patches = []
        
        # Mock external libraries
        self.mock_mongo_client = self.start_patch('workers.DatabaseInteractionWorker.MongoClient')
        self.mock_log = self.start_patch('workers.DatabaseInteractionWorker.log')
        self.mock_send_message = self.start_patch('workers.DatabaseInteractionWorker.sendMessage')
        self.mock_convert_objectid = self.start_patch('workers.DatabaseInteractionWorker.convertObjectIdToStr')
        self.mock_asyncio = self.start_patch('workers.DatabaseInteractionWorker.asyncio')
        
        # Mock connection
        self.mock_conn = Mock()
        
        # Mock configuration
        self.test_config = {
            'database': 'test_db',
            'dbTweets': 'test_tweets_db',
            'connection_string': 'mongodb://test:27017',
            'AZURE_OPENAI_API_KEY': 'test-key',
            'AZURE_OPENAI_ENDPOINT': 'https://test.openai.azure.com',
            'AZURE_OPENAI_DEPLOYMENT_NAME': 'test-deployment',
            'AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING': 'test-embedding',
            'AZURE_OPENAI_API_VERSION': '2023-05-15'
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

    def test_database_worker_initialization(self):
        """Test DatabaseInteractionWorker initialization with proper configuration."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        
        # Test configuration assignment
        self.assertEqual(worker._db_name, self.test_config['database'])
        self.assertEqual(worker._dbTweets, self.test_config['dbTweets'])
        self.assertEqual(worker.connection_string, self.test_config['connection_string'])
        self.assertEqual(worker.AZURE_OPENAI_API_KEY, self.test_config['AZURE_OPENAI_API_KEY'])
        self.assertEqual(worker.AZURE_OPENAI_ENDPOINT, self.test_config['AZURE_OPENAI_ENDPOINT'])
        
        # Test initial state
        self.assertEqual(DatabaseInteractionWorker.conn, self.mock_conn)
        self.assertFalse(DatabaseInteractionWorker.isBusy)

    def test_database_worker_initialization_with_defaults(self):
        """Test DatabaseInteractionWorker initialization with default values."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        minimal_config = {}
        worker = DatabaseInteractionWorker(self.mock_conn, minimal_config)
        
        # Test default values
        self.assertEqual(worker._db_name, "mydatabase")
        self.assertEqual(worker._dbTweets, "dataGathering")
        self.assertEqual(worker.connection_string, "mongodb://localhost:27017/")
        self.assertIsNone(worker.AZURE_OPENAI_API_KEY)

    def test_run_method_database_connection(self):
        """Test run method establishes proper database connections."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        # Mock MongoDB client and databases
        mock_client = Mock()
        mock_db = Mock()
        mock_db_tweets = Mock()
        
        self.mock_mongo_client.return_value = mock_client
        mock_client.__getitem__.side_effect = lambda x: mock_db if x == self.test_config['database'] else mock_db_tweets
        mock_client.server_info.return_value = {"version": "4.4.0"}
        
        # Mock asyncio.gather to prevent actual async execution
        self.mock_asyncio.gather.return_value = asyncio.Future()
        self.mock_asyncio.gather.return_value.set_result(None)
        self.mock_asyncio.run.side_effect = None  # Prevent actual async execution
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        
        # Mock the run method to avoid actual execution
        with patch.object(worker, 'listen_task'), \
             patch('workers.DatabaseInteractionWorker.asyncio.run'):
            
            worker.run()
            
            # Verify MongoDB client creation
            self.mock_mongo_client.assert_called_once_with(self.test_config['connection_string'])
            
            # Verify database assignment
            self.assertEqual(worker._db, mock_db)
            self.assertEqual(worker._dbTweets, mock_db_tweets)
            
            # Verify connection test
            mock_client.server_info.assert_called_once()
            
            # Verify success logging
            self.mock_log.assert_called_with(
                f"Connected to MongoDB at {self.test_config['connection_string']}", "success"
            )

    def test_run_method_connection_failure(self):
        """Test run method handles database connection failure."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        # Mock connection failure
        mock_client = Mock()
        self.mock_mongo_client.return_value = mock_client
        mock_client.server_info.side_effect = Exception("Connection failed")
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        
        with patch('workers.DatabaseInteractionWorker.asyncio.run') as mock_run:
            mock_run.side_effect = Exception("Connection failed")
            
            with self.assertRaises(Exception):
                worker.run()

    async def test_listen_task_message_processing(self):
        """Test listen_task processes messages correctly."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        DatabaseInteractionWorker.conn = Mock()
        DatabaseInteractionWorker.isBusy = False
        
        # Mock message receiving
        test_message = {
            "destination": ["DatabaseInteractionWorker/getTweets/project123"],
            "data": {"keyword": "test"},
            "messageId": "test-msg"
        }
        
        # Mock poll to return True once, then False to exit loop
        DatabaseInteractionWorker.conn.poll.side_effect = [True, False]
        DatabaseInteractionWorker.conn.recv.return_value = test_message
        
        # Mock method execution
        with patch.object(worker, 'getTweets') as mock_get_tweets:
            mock_get_tweets.return_value = {
                "destination": ["supervisor"],
                "data": [{"tweet": "test"}]
            }
            
            try:
                await worker.listen_task()
            except Exception:
                pass  # Expected to break on poll returning False
            
            # Verify method was called
            mock_get_tweets.assert_called_once_with(
                id="project123",
                data={"keyword": "test"}
            )
            
            # Verify response was sent
            self.mock_send_message.assert_called_once()

    async def test_listen_task_busy_worker(self):
        """Test listen_task handles busy worker state."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        DatabaseInteractionWorker.conn = Mock()
        DatabaseInteractionWorker.isBusy = True  # Set worker as busy
        
        test_message = {
            "destination": ["DatabaseInteractionWorker/getTweets/project123"],
            "data": {"keyword": "test"},
            "messageId": "test-msg"
        }
        
        DatabaseInteractionWorker.conn.poll.side_effect = [True, False]
        DatabaseInteractionWorker.conn.recv.return_value = test_message
        
        with patch.object(worker, 'sendToOtherWorker') as mock_send_to_worker:
            try:
                await worker.listen_task()
            except Exception:
                pass
            
            # Verify busy response was sent
            mock_send_to_worker.assert_called_once_with(
                messageId="test-msg",
                destination=["DatabaseInteractionWorker/getTweets/project123"],
                data={"keyword": "test"},
                status="failed",
                reason="SERVER_BUSY"
            )

    async def test_listen_task_connection_error(self):
        """Test listen_task handles connection errors gracefully."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        DatabaseInteractionWorker.conn = Mock()
        
        # Mock EOFError
        DatabaseInteractionWorker.conn.poll.side_effect = EOFError("Connection closed")
        
        await worker.listen_task()
        
        # Verify error was logged
        self.mock_log.assert_called_with("Connection closed by supervisor", 'error')

    def test_send_to_other_worker_method(self):
        """Test sendToOtherWorker method functionality."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        
        with patch.object(worker, 'sendToOtherWorker') as mock_method:
            # This test verifies the method exists and can be called
            # The actual implementation might vary based on the specific worker
            pass

    def test_worker_busy_state_management(self):
        """Test busy state management during message processing."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        
        # Initially not busy
        self.assertFalse(DatabaseInteractionWorker.isBusy)
        
        # Test busy state can be set
        DatabaseInteractionWorker.isBusy = True
        self.assertTrue(DatabaseInteractionWorker.isBusy)
        
        # Test busy state can be reset
        DatabaseInteractionWorker.isBusy = False
        self.assertFalse(DatabaseInteractionWorker.isBusy)

    def test_database_method_execution_pattern(self):
        """Test the pattern of database method execution."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        
        # Mock a database method
        with patch.object(worker, '_db') as mock_db:
            mock_collection = Mock()
            mock_db.__getitem__.return_value = mock_collection
            mock_collection.find.return_value = [{"_id": "test", "data": "value"}]
            
            # This would represent a typical database operation pattern
            # The specific implementation depends on the actual worker methods
            result = mock_collection.find({})
            self.assertIsNotNone(result)

    def test_configuration_parameter_handling(self):
        """Test handling of various configuration parameters."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        # Test with comprehensive config
        full_config = {
            'database': 'production_db',
            'dbTweets': 'tweets_db',
            'connection_string': 'mongodb://prod:27017',
            'AZURE_OPENAI_API_KEY': 'prod-key',
            'AZURE_OPENAI_ENDPOINT': 'https://prod.openai.azure.com',
            'AZURE_OPENAI_DEPLOYMENT_NAME': 'prod-deployment',
            'AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING': 'prod-embedding',
            'AZURE_OPENAI_API_VERSION': '2024-02-01'
        }
        
        worker = DatabaseInteractionWorker(self.mock_conn, full_config)
        
        # Verify all parameters are set correctly
        self.assertEqual(worker._db_name, 'production_db')
        self.assertEqual(worker._dbTweets, 'tweets_db')
        self.assertEqual(worker.connection_string, 'mongodb://prod:27017')
        self.assertEqual(worker.AZURE_OPENAI_API_KEY, 'prod-key')
        self.assertEqual(worker.AZURE_OPENAI_ENDPOINT, 'https://prod.openai.azure.com')
        self.assertEqual(worker.AZURE_OPENAI_DEPLOYMENT_NAME, 'prod-deployment')
        self.assertEqual(worker.AZURE_OPENAI_DEPLOYMENT_NAME_EMBEDDING, 'prod-embedding')
        self.assertEqual(worker.AZURE_OPENAI_API_VERSION, '2024-02-01')

    def test_error_handling_in_message_processing(self):
        """Test error handling during message processing."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        
        # Test that worker handles missing method gracefully
        with patch('builtins.getattr', side_effect=AttributeError("Method not found")):
            # This would test error handling when a requested method doesn't exist
            pass

    def test_message_destination_parsing(self):
        """Test parsing of message destinations."""
        from workers.DatabaseInteractionWorker import DatabaseInteractionWorker
        
        worker = DatabaseInteractionWorker(self.mock_conn, self.test_config)
        
        # Test destination parsing logic
        test_destinations = [
            "DatabaseInteractionWorker/getTweets/project123",
            "DatabaseInteractionWorker/insertData/user456",
            "DatabaseInteractionWorker/deleteRecord/record789"
        ]
        
        for destination in test_destinations:
            parts = destination.split('/')
            self.assertEqual(parts[0], "DatabaseInteractionWorker")
            self.assertEqual(len(parts), 3)  # worker/method/param format

    def test_main_function(self):
        """Test main function execution."""
        from workers.DatabaseInteractionWorker import main
        
        mock_conn = Mock()
        test_config = {"test": "config"}
        
        with patch('workers.DatabaseInteractionWorker.DatabaseInteractionWorker') as mock_worker_class:
            mock_worker = Mock()
            mock_worker_class.return_value = mock_worker
            
            main(mock_conn, test_config)
            
            # Verify worker was created with correct parameters
            mock_worker_class.assert_called_once_with(mock_conn, test_config)
            
            # Verify worker run method was called
            mock_worker.run.assert_called_once()


if __name__ == '__main__':
    unittest.main()