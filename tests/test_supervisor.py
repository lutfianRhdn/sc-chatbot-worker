"""
Comprehensive unit tests for the Supervisor class.

Tests cover:
- Worker creation and management
- Health checking functionality
- Message routing between workers
- Error handling and worker recovery
- Pending message tracking and resending
- Worker termination and cleanup
"""

import unittest
from unittest.mock import Mock, patch, MagicMock, call
import multiprocessing
import time
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from supervisor import Supervisor


class TestSupervisor(unittest.TestCase):
    """Test cases for Supervisor class functionality."""

    def setUp(self):
        """Set up test fixtures before each test method."""
        # Mock all external dependencies
        self.mock_log_patcher = patch('supervisor.log')
        self.mock_psutil_patcher = patch('supervisor.psutil')
        self.mock_multiprocessing_patcher = patch('supervisor.multiprocessing')
        self.mock_importlib_patcher = patch('supervisor.importlib')
        
        self.mock_log = self.mock_log_patcher.start()
        self.mock_psutil = self.mock_psutil_patcher.start()
        self.mock_multiprocessing = self.mock_multiprocessing_patcher.start()
        self.mock_importlib = self.mock_importlib_patcher.start()
        
        # Mock pipe creation
        self.mock_parent_conn = Mock()
        self.mock_child_conn = Mock()
        self.mock_multiprocessing.Pipe.return_value = (self.mock_parent_conn, self.mock_child_conn)
        
        # Mock process creation
        self.mock_process = Mock()
        self.mock_process.pid = 12345
        self.mock_process.is_alive.return_value = True
        self.mock_multiprocessing.Process.return_value = self.mock_process
        
        # Mock psutil functions
        self.mock_psutil.pid_exists.return_value = True
        self.mock_psutil.Process.return_value.status.return_value = 'running'
        self.mock_psutil.STATUS_ZOMBIE = 'zombie'
        self.mock_psutil.STATUS_DEAD = 'dead'

    def tearDown(self):
        """Clean up after each test method."""
        self.mock_log_patcher.stop()
        self.mock_psutil_patcher.stop()
        self.mock_multiprocessing_patcher.stop()
        self.mock_importlib_patcher.stop()

    @patch('supervisor.threading')
    def test_supervisor_initialization(self, mock_threading):
        """Test that supervisor initializes correctly with default workers."""
        # Mock thread creation
        mock_thread = Mock()
        mock_threading.Thread.return_value = mock_thread
        
        with patch.object(Supervisor, 'create_worker') as mock_create_worker:
            supervisor = Supervisor()
            
            # Verify all default workers are created
            expected_calls = [
                call("RestApiWorker", count=1, config=unittest.mock.ANY),
                call("CRAGWorker", count=1, config=unittest.mock.ANY),
                call("DatabaseInteractionWorker", count=1, config=unittest.mock.ANY),
                call("VectorWorker", count=1, config=unittest.mock.ANY),
                call("PromptRecommendationWorker", count=1, config=unittest.mock.ANY),
                call("RabbitMQWorker", count=1, config=unittest.mock.ANY),
                call("LogicalFallacyPromptWorker", count=1, config=unittest.mock.ANY),
                call("SMTConverterWorker", count=1, config=unittest.mock.ANY),
                call("CounterExampleCreatorWorker", count=1, config=unittest.mock.ANY),
                call("LogicalFallacyClassificationWorker", count=1, config=unittest.mock.ANY),
                call("LogicalFallacyResponseWorker", count=1, config=unittest.mock.ANY),
            ]
            mock_create_worker.assert_has_calls(expected_calls, any_order=False)
            
            # Verify health check thread is started
            mock_thread.start.assert_called_once()
            self.mock_log.assert_called_with("Supervisor initialized", "info")

    def test_create_worker_success(self):
        """Test successful worker creation."""
        supervisor = Supervisor.__new__(Supervisor)  # Create without calling __init__
        supervisor._workers = {}
        supervisor.pending_messages = {}
        
        with patch.object(supervisor, '_start_listener') as mock_start_listener, \
             patch.object(supervisor, 'resend_pending_messages') as mock_resend:
            
            supervisor.create_worker("TestWorker", count=2, config={"test": "config"})
            
            # Verify process creation
            self.assertEqual(self.mock_multiprocessing.Process.call_count, 2)
            self.mock_process.start.assert_called()
            
            # Verify workers are tracked
            self.assertIn(12345, supervisor._workers)
            worker_info = supervisor._workers[12345]
            self.assertEqual(worker_info["name"], "TestWorker")
            self.assertEqual(worker_info["process"], self.mock_process)
            self.assertEqual(worker_info["conn"], self.mock_parent_conn)
            
            # Verify listener and pending message handling
            mock_start_listener.assert_called_with(12345)
            mock_resend.assert_called_with("TestWorker")

    def test_create_worker_invalid_count(self):
        """Test worker creation with invalid count raises error."""
        supervisor = Supervisor.__new__(Supervisor)
        
        with self.assertRaises(ValueError) as context:
            supervisor.create_worker("TestWorker", count=0)
        
        self.assertEqual(str(context.exception), "Worker count must be greater than zero")
        self.mock_log.assert_called_with("Worker count must be greater than zero", "error")

    @patch('supervisor.threading.Thread')
    def test_start_listener(self, mock_thread_class):
        """Test listener thread creation and message handling."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {12345: {"conn": self.mock_parent_conn, "name": "TestWorker"}}
        
        # Mock thread
        mock_thread = Mock()
        mock_thread_class.return_value = mock_thread
        
        with patch.object(supervisor, 'handle_worker_message') as mock_handle:
            supervisor._start_listener(12345)
            
            # Verify thread creation and start
            mock_thread_class.assert_called_once()
            mock_thread.start.assert_called_once()
            
            # Get the listener function that was passed to Thread
            listener_func = mock_thread_class.call_args[1]['target']
            
            # Test successful message receiving
            test_message = {"test": "message"}
            self.mock_parent_conn.poll.return_value = True
            self.mock_parent_conn.recv.return_value = test_message
            
            with patch('supervisor.convertMessage') as mock_convert:
                mock_convert.return_value = test_message
                try:
                    listener_func()
                except Exception:
                    pass  # Expected due to infinite loop
                
                mock_handle.assert_called()

    def test_worker_runner_success(self):
        """Test successful worker runner execution."""
        mock_conn = Mock()
        config = {"test": "config"}
        
        # Mock successful module import and execution
        mock_module = Mock()
        self.mock_importlib.import_module.return_value = mock_module
        
        Supervisor._worker_runner("TestWorker", mock_conn, config)
        
        # Verify module import and execution
        self.mock_importlib.import_module.assert_called_with("workers.TestWorker")
        mock_module.main.assert_called_with(mock_conn, config)
        mock_conn.close.assert_called_once()

    def test_worker_runner_module_not_found(self):
        """Test worker runner handling of missing module."""
        mock_conn = Mock()
        config = {"test": "config"}
        
        # Mock module not found error
        self.mock_importlib.import_module.side_effect = ModuleNotFoundError("No module")
        
        Supervisor._worker_runner("TestWorker", mock_conn, config)
        
        # Verify error logging and connection cleanup
        self.mock_log.assert_called_with("Worker module not found: workers.TestWorker", "error")
        mock_conn.close.assert_called_once()

    def test_check_worker_health_healthy_worker(self):
        """Test health check for healthy worker."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {
            12345: {"process": self.mock_process, "name": "TestWorker"}
        }
        
        # Mock healthy worker
        self.mock_psutil.pid_exists.return_value = True
        mock_psutil_process = Mock()
        mock_psutil_process.status.return_value = 'running'
        self.mock_psutil.Process.return_value = mock_psutil_process
        
        with patch.object(supervisor, '_kill_worker') as mock_kill, \
             patch.object(supervisor, 'create_worker') as mock_create:
            
            supervisor.check_worker_health()
            
            # Verify worker is not killed or recreated
            mock_kill.assert_not_called()
            mock_create.assert_not_called()

    def test_check_worker_health_dead_worker(self):
        """Test health check for dead worker."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {
            12345: {"process": self.mock_process, "name": "TestWorker"}
        }
        
        # Mock dead worker
        self.mock_psutil.pid_exists.return_value = False
        
        with patch.object(supervisor, '_kill_worker') as mock_kill, \
             patch.object(supervisor, 'create_worker') as mock_create, \
             patch('supervisor.allConfigs', {'TestWorker': {'config': 'value'}}):
            
            supervisor.check_worker_health()
            
            # Verify worker is killed and recreated
            mock_kill.assert_called_with(12345)
            mock_create.assert_called_with("TestWorker", count=1, config={'config': 'value'})
            self.mock_log.assert_called_with(
                "Worker TestWorker (12345) is not alive, removing from tracking", "warn"
            )

    def test_handle_worker_message_routing(self):
        """Test message routing to other workers."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {}
        supervisor.workers_health = {}
        supervisor.pending_messages = {}
        
        message = {
            'destination': ['OtherWorker/method/param'],
            'status': 'completed',
            'messageId': 'test-123'
        }
        
        with patch.object(supervisor, '_send_to_worker') as mock_send:
            supervisor.handle_worker_message(message, 12345)
            
            mock_send.assert_called_with('OtherWorker/method/param', message)

    def test_handle_worker_message_health_update(self):
        """Test health message handling."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {12345: {"name": "TestWorker"}}
        supervisor.workers_health = {}
        supervisor.pending_messages = {}
        
        message = {
            'destination': ['supervisor'],
            'status': 'healthy',
            'messageId': 'TestWorker-instance-123'
        }
        
        with patch('time.time', return_value=123456789):
            supervisor.handle_worker_message(message, 12345)
            
            # Verify health status update
            self.assertIn(12345, supervisor.workers_health)
            health_info = supervisor.workers_health[12345]
            self.assertTrue(health_info['is_healthy'])
            self.assertEqual(health_info['worker_name'], 'TestWorker')
            self.assertEqual(health_info['timestamp'], 123456789)

    def test_send_to_worker_success(self):
        """Test successful message sending to worker."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {
            12345: {
                "name": "TestWorker",
                "conn": self.mock_parent_conn,
                "process": self.mock_process
            }
        }
        supervisor.pending_messages = {}
        
        message = {
            'messageId': 'test-123',
            'status': 'completed',
            'reason': 'success',
            'data': {'test': 'data'}
        }
        
        with patch.object(supervisor, 'track_pending_message') as mock_track:
            supervisor._send_to_worker('TestWorker/method', message)
            
            # Verify message tracking and sending
            mock_track.assert_called_with('TestWorker', message)
            self.mock_parent_conn.send.assert_called_with(message)
            self.mock_log.assert_called_with(
                "Sending message to worker: TestWorker, PID: 12345, Method: method, "
                "Message ID: test-123, Status: completed, Reason: success", "info"
            )

    def test_send_to_worker_no_available_worker(self):
        """Test message sending when no worker is available."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {}
        supervisor.pending_messages = {}
        
        message = {
            'messageId': 'test-123',
            'status': 'completed'
        }
        
        with patch.object(supervisor, 'track_pending_message') as mock_track, \
             patch('supervisor.threading.Timer') as mock_timer:
            
            supervisor._send_to_worker('TestWorker/method', message)
            
            # Verify pending message tracking and retry setup
            mock_track.assert_called_with('TestWorker', message)
            self.mock_log.assert_called_with(
                "No available worker for destination: TestWorker/method", "warn"
            )
            mock_timer.assert_called_once()

    def test_track_pending_message(self):
        """Test pending message tracking."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor.pending_messages = {}
        
        message = {'messageId': 'test-123', 'data': 'test'}
        
        supervisor.track_pending_message('TestWorker', message)
        
        self.assertIn('TestWorker', supervisor.pending_messages)
        self.assertIn(message, supervisor.pending_messages['TestWorker'])

    def test_remove_pending_message(self):
        """Test pending message removal."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor.pending_messages = {
            'TestWorker': [
                {'messageId': 'test-123', 'data': 'test1'},
                {'messageId': 'test-456', 'data': 'test2'}
            ]
        }
        
        supervisor.remove_pending_message('TestWorker', 'test-123')
        
        # Verify only the correct message was removed
        remaining_messages = supervisor.pending_messages['TestWorker']
        self.assertEqual(len(remaining_messages), 1)
        self.assertEqual(remaining_messages[0]['messageId'], 'test-456')

    def test_resend_pending_messages(self):
        """Test resending of pending messages."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {
            12345: {
                "name": "TestWorker",
                "conn": self.mock_parent_conn
            }
        }
        supervisor.pending_messages = {
            'TestWorker': [
                {'messageId': 'test-123', 'data': 'test1'},
                {'messageId': 'test-456', 'data': 'test2'}
            ]
        }
        
        supervisor.resend_pending_messages('TestWorker')
        
        # Verify all pending messages were sent
        self.assertEqual(self.mock_parent_conn.send.call_count, 2)
        self.mock_log.assert_any_call("Resending 2 pending messages to TestWorker", "info")

    def test_kill_worker(self):
        """Test worker termination."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {
            12345: {
                "conn": self.mock_parent_conn,
                "process": self.mock_process
            }
        }
        
        supervisor._kill_worker(12345)
        
        # Verify worker cleanup
        self.assertNotIn(12345, supervisor._workers)
        self.mock_parent_conn.close.assert_called_once()
        self.mock_process.terminate.assert_called_once()

    def test_is_worker_alive(self):
        """Test worker alive status check."""
        supervisor = Supervisor.__new__(Supervisor)
        supervisor._workers = {
            12345: {"process": self.mock_process}
        }
        
        # Test alive worker
        self.mock_process.is_alive.return_value = True
        self.assertTrue(supervisor.is_worker_alive(12345))
        
        # Test dead worker
        self.mock_process.is_alive.return_value = False
        self.assertFalse(supervisor.is_worker_alive(12345))
        
        # Test non-existent worker
        self.assertFalse(supervisor.is_worker_alive(99999))


if __name__ == '__main__':
    unittest.main()