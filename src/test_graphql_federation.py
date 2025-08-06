#!/usr/bin/env python3
"""
Test script for GraphQL Federation Subgraph 2 Worker
This script tests the functionality without requiring all dependencies.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

def test_graphql_federation_worker():
    """Test the GraphQL Federation Worker functionality"""
    print("🔧 Testing GraphQL Federation Subgraph 2 Worker")
    print("=" * 60)
    
    try:
        # Test json_response_types
        print("1. Testing json_response_types...")
        import json_response_types
        
        # Test decorator
        @json_response_types.json_response_types(json_response_types.ChatEntity)
        def test_function():
            return "test"
        
        print("   ✓ @json_response_types decorator works")
        
        # Test response creation helpers
        success_resp = json_response_types.create_success_response("Test success", {"key": "value"})
        error_resp = json_response_types.create_error_response("Test error")
        processing_resp = json_response_types.create_processing_response("Test processing")
        
        print("   ✓ Response creation helpers work")
        print(f"     - Success: {success_resp.status}")
        print(f"     - Error: {error_resp.status}")
        print(f"     - Processing: {processing_resp.status}")
        
        # Test entity creation
        chat_entity = json_response_types.ChatEntity(
            id="test-123",
            chat_id="chat-456",
            prompt="Test prompt",
            project_id="proj-789"
        )
        print(f"   ✓ ChatEntity created: {chat_entity.id}")
        
        prompt_entity = json_response_types.PromptEntity(
            id="prompt-123",
            project_id="proj-456"
        )
        print(f"   ✓ PromptEntity created: {prompt_entity.id}")
        
        progress_entity = json_response_types.ProgressEntity(
            id="progress-123",
            chat_id="chat-789",
            progress_name="test_progress"
        )
        print(f"   ✓ ProgressEntity created: {progress_entity.id}")
        
    except Exception as e:
        print(f"   ✗ Error in json_response_types: {e}")
        return False
    
    try:
        # Test GraphQL Worker
        print("\n2. Testing GraphQLFederationSubgraph2Worker...")
        from workers.GraphQLFederationSubgraph2Worker import GraphQLFederationSubgraph2Worker
        
        worker = GraphQLFederationSubgraph2Worker()
        print("   ✓ Worker instance created")
        
        # Test federation schema
        schema = worker.get_federation_schema()
        print(f"   ✓ Federation schema generated: {schema['subgraph']}")
        print(f"     - Version: {schema['version']}")
        print(f"     - Entities: {len(schema['entities'])}")
        print(f"     - Resolvers: {len(schema['resolvers'])}")
        
        # Test schema structure
        for entity_name, entity_config in schema['entities'].items():
            print(f"     - {entity_name}: {len(entity_config['fields'])} fields, keys: {entity_config['keys']}")
        
        # Test resolver registration
        expected_resolvers = [
            'resolve_chat', 'resolve_prompt', 'resolve_progress',
            'query_chat_by_id', 'query_prompt_by_project',
            'mutation_create_chat', 'mutation_create_chat_crag', 'mutation_create_chat_response'
        ]
        
        for resolver in expected_resolvers:
            if resolver in worker.resolvers:
                print(f"   ✓ Resolver '{resolver}' registered")
            else:
                print(f"   ✗ Resolver '{resolver}' missing")
                return False
                
    except Exception as e:
        print(f"   ✗ Error in GraphQLFederationSubgraph2Worker: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    try:
        # Test worker configuration
        print("\n3. Testing worker configuration...")
        from config.workerConfig import GraphQLFederationSubgraph2WorkerConfig, allConfigs
        
        print(f"   ✓ Config loaded: port {GraphQLFederationSubgraph2WorkerConfig['port']}")
        print(f"   ✓ Subgraph name: {GraphQLFederationSubgraph2WorkerConfig['subgraph_name']}")
        print(f"   ✓ Federation version: {GraphQLFederationSubgraph2WorkerConfig['federation_version']}")
        
        if 'GraphQLFederationSubgraph2Worker' in allConfigs:
            print("   ✓ Worker config registered in allConfigs")
        else:
            print("   ✗ Worker config not found in allConfigs")
            return False
            
    except Exception as e:
        print(f"   ✗ Error in worker configuration: {e}")
        return False
    
    print("\n4. Testing GraphQL Federation Schema Compliance...")
    
    # Test federation key compliance
    federation_entities = ['Chat', 'Prompt', 'Progress']
    federation_keys = {
        'Chat': ['chat_id'],
        'Prompt': ['project_id'],
        'Progress': ['chat_id', 'progress_name']
    }
    
    for entity in federation_entities:
        if entity in worker.federation_schema:
            entity_keys = worker.federation_schema[entity]['keys']
            expected_keys = federation_keys[entity]
            if entity_keys == expected_keys:
                print(f"   ✓ {entity} federation keys correct: {entity_keys}")
            else:
                print(f"   ✗ {entity} federation keys incorrect: got {entity_keys}, expected {expected_keys}")
                return False
        else:
            print(f"   ✗ {entity} not found in federation schema")
            return False
    
    print("\n🎉 All tests passed! GraphQL Federation Subgraph 2 Worker is ready.")
    print("\n📋 Implementation Summary:")
    print("   • Created json_response_types.py with @json_response_types decorator")
    print("   • Implemented GraphQLFederationSubgraph2Worker with federation schema")
    print("   • Added entity resolvers for Chat, Prompt, and Progress")
    print("   • Implemented GraphQL queries and mutations matching REST API")
    print("   • Configured worker in supervisor and worker config")
    print("   • Federation-compliant schema with proper entity keys")
    print("   • Inter-worker communication using existing message system")
    
    return True

if __name__ == "__main__":
    success = test_graphql_federation_worker()
    sys.exit(0 if success else 1)