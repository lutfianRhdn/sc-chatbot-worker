"""
Comprehensive unit tests for the Worker base class.

Tests cover:
- Abstract method enforcement
- Worker interface compliance
- Class structure validation
"""

import unittest
from unittest.mock import Mock, patch
import sys
import os

# Add src directory to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from workers.Worker import Worker


class TestWorker(unittest.TestCase):
    """Test cases for Worker base class functionality."""

    def test_worker_is_abstract_base_class(self):
        """Test that Worker is properly defined as an abstract base class."""
        from abc import ABC
        
        # Verify Worker inherits from ABC
        self.assertTrue(issubclass(Worker, ABC))

    def test_cannot_instantiate_worker_directly(self):
        """Test that Worker cannot be instantiated directly due to abstract methods."""
        with self.assertRaises(TypeError) as context:
            Worker()
        
        # Check that the error mentions abstract methods
        error_message = str(context.exception)
        self.assertIn("abstract", error_message.lower())
        self.assertIn("run", error_message)
        self.assertIn("listen_task", error_message)

    def test_abstract_methods_defined(self):
        """Test that required abstract methods are properly defined."""
        import inspect
        
        # Get abstract methods
        abstract_methods = Worker.__abstractmethods__
        
        # Verify required abstract methods exist
        self.assertIn('run', abstract_methods)
        self.assertIn('listen_task', abstract_methods)
        
        # Verify method signatures
        run_method = getattr(Worker, 'run')
        listen_task_method = getattr(Worker, 'listen_task')
        
        # Check that methods are properly marked as abstract
        self.assertTrue(hasattr(run_method, '__isabstractmethod__'))
        self.assertTrue(hasattr(listen_task_method, '__isabstractmethod__'))

    def test_concrete_worker_implementation(self):
        """Test that a concrete implementation of Worker can be instantiated."""
        
        class ConcreteWorker(Worker):
            async def run(self):
                return "run called"
            
            async def listen_task(self):
                return "listen_task called"
        
        # Should be able to instantiate concrete implementation
        worker = ConcreteWorker()
        self.assertIsInstance(worker, Worker)
        self.assertIsInstance(worker, ConcreteWorker)

    def test_partial_implementation_raises_error(self):
        """Test that partial implementation of Worker raises TypeError."""
        
        # Only implement run method, not listen_task
        class PartialWorker(Worker):
            async def run(self):
                return "run called"
            # Missing listen_task implementation
        
        with self.assertRaises(TypeError) as context:
            PartialWorker()
        
        error_message = str(context.exception)
        self.assertIn("abstract", error_message.lower())
        self.assertIn("listen_task", error_message)

    def test_abstract_method_signatures(self):
        """Test that abstract methods have correct signatures."""
        import inspect
        
        # Check run method signature
        run_signature = inspect.signature(Worker.run)
        self.assertEqual(len(run_signature.parameters), 1)  # Only 'self' parameter
        
        # Check listen_task method signature
        listen_task_signature = inspect.signature(Worker.listen_task)
        self.assertEqual(len(listen_task_signature.parameters), 1)  # Only 'self' parameter
        
        # Check return type annotations
        self.assertEqual(run_signature.return_annotation, None)
        self.assertEqual(listen_task_signature.return_annotation, None)

    def test_docstring_documentation(self):
        """Test that abstract methods have proper documentation."""
        
        # Check that run method has docstring
        run_docstring = Worker.run.__doc__
        self.assertIsNotNone(run_docstring)
        self.assertIn("main task", run_docstring)
        self.assertIn("overridden", run_docstring)
        
        # Check that listen_task method has docstring
        listen_task_docstring = Worker.listen_task.__doc__
        self.assertIsNotNone(listen_task_docstring)
        self.assertIn("task", listen_task_docstring)
        self.assertIn("overridden", listen_task_docstring)

    def test_method_raises_not_implemented_error(self):
        """Test that abstract methods raise NotImplementedError when called directly."""
        
        # Create a mock instance to test the method behavior
        # We can't instantiate Worker directly, but we can test the method implementation
        
        class TestableWorker(Worker):
            # Implement required abstract methods to allow instantiation
            async def run(self):
                # Call the parent's run method to test NotImplementedError
                return await super().run()
            
            async def listen_task(self):
                # Call the parent's listen_task method to test NotImplementedError
                return await super().listen_task()
        
        worker = TestableWorker()
        
        # Test that calling parent's run method raises NotImplementedError
        import asyncio
        
        with self.assertRaises(NotImplementedError):
            asyncio.run(worker.run())
        
        with self.assertRaises(NotImplementedError):
            asyncio.run(worker.listen_task())

    def test_worker_inheritance_chain(self):
        """Test the inheritance chain and method resolution order."""
        
        class ConcreteWorker(Worker):
            async def run(self):
                return "concrete run"
            
            async def listen_task(self):
                return "concrete listen_task"
        
        worker = ConcreteWorker()
        
        # Test method resolution order
        mro = ConcreteWorker.__mro__
        self.assertEqual(mro[0], ConcreteWorker)
        self.assertEqual(mro[1], Worker)
        
        # Test that methods are properly overridden
        import asyncio
        self.assertEqual(asyncio.run(worker.run()), "concrete run")
        self.assertEqual(asyncio.run(worker.listen_task()), "concrete listen_task")

    def test_multiple_inheritance_compatibility(self):
        """Test that Worker can be used in multiple inheritance scenarios."""
        
        class Mixin:
            def mixin_method(self):
                return "mixin called"
        
        class MultipleInheritanceWorker(Worker, Mixin):
            async def run(self):
                return "multiple inheritance run"
            
            async def listen_task(self):
                return "multiple inheritance listen_task"
        
        worker = MultipleInheritanceWorker()
        
        # Test that both interfaces work
        self.assertIsInstance(worker, Worker)
        self.assertIsInstance(worker, Mixin)
        self.assertEqual(worker.mixin_method(), "mixin called")
        
        import asyncio
        self.assertEqual(asyncio.run(worker.run()), "multiple inheritance run")
        self.assertEqual(asyncio.run(worker.listen_task()), "multiple inheritance listen_task")

    def test_async_method_requirements(self):
        """Test that abstract methods are properly defined as async."""
        import inspect
        
        # Check that abstract methods are async
        self.assertTrue(inspect.iscoroutinefunction(Worker.run))
        self.assertTrue(inspect.iscoroutinefunction(Worker.listen_task))

    def test_worker_class_attributes(self):
        """Test Worker class has expected attributes and structure."""
        
        # Test that Worker has the expected abstract methods
        expected_abstract_methods = {'run', 'listen_task'}
        self.assertEqual(Worker.__abstractmethods__, frozenset(expected_abstract_methods))
        
        # Test that Worker doesn't have any concrete methods
        concrete_methods = [method for method in dir(Worker) 
                          if not method.startswith('_') and callable(getattr(Worker, method))
                          and not hasattr(getattr(Worker, method), '__isabstractmethod__')]
        
        # Should only have inherited methods from ABC and object
        self.assertEqual(len(concrete_methods), 0)


if __name__ == '__main__':
    unittest.main()