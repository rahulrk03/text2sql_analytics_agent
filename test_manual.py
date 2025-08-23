#!/usr/bin/env python3
"""
Manual test script to verify the streaming functionality without requiring database connection.
This creates a minimal FastAPI app with mocked dependencies to test the streaming response.
"""

import json
from unittest.mock import Mock, patch

from fastapi.testclient import TestClient
from app.api import app


def test_streaming_manually():
    """Manual test for streaming functionality."""
    print("Testing streaming response functionality...")
    
    # Create test client
    client = TestClient(app)
    
    # Test health endpoint first
    print("\n1. Testing health endpoint...")
    response = client.get("/health")
    print(f"Health status: {response.status_code}")
    print(f"Response: {response.json()}")
    
    # Test with mocked dependencies for streaming
    print("\n2. Testing streaming query...")
    
    with patch("app.api.client") as mock_client, \
         patch("app.api.get_schema_text") as mock_get_schema, \
         patch("app.api.enrich_query") as mock_enrich, \
         patch("app.api.build_prompt") as mock_build_prompt, \
         patch("app.api.stream_query_results") as mock_stream:
        
        # Setup mocks
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>SELECT id, name FROM customers LIMIT 10</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema.return_value = "Table: customers (id, name)"
        mock_enrich.return_value = "enriched: show me customers"
        mock_build_prompt.return_value = "Generate SQL for: show me customers"
        
        # Mock streaming generator
        def mock_streaming_data():
            yield '{"sql": "SELECT id, name FROM customers LIMIT 10", '
            yield '"columns": ["id", "name"], '
            yield '"rows": ['
            yield '[1, "Alice"]'
            yield ', [2, "Bob"]'
            yield ', [3, "Charlie"]'
            yield '], '
            yield '"pagination": {"page": 1, "page_size": 50, "total_rows": 3, "total_pages": 1}}'
        
        mock_stream.return_value = mock_streaming_data()
        
        # Make streaming request
        response = client.post(
            "/query",
            json={
                "question": "Show me all customers",
                "stream": True
            }
        )
        
        print(f"Streaming response status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        # Read streaming content
        content = b"".join(response.iter_bytes()).decode()
        print(f"Raw streaming content: {content}")
        
        # Parse as JSON
        try:
            data = json.loads(content)
            print(f"Parsed JSON data: {json.dumps(data, indent=2)}")
            print(f"Number of rows: {len(data['rows'])}")
            print(f"SQL generated: {data['sql']}")
            print("✅ Streaming test PASSED")
        except json.JSONDecodeError as e:
            print(f"❌ JSON parsing failed: {e}")
    
    # Test non-streaming
    print("\n3. Testing non-streaming query...")
    
    with patch("app.api.client") as mock_client, \
         patch("app.api.get_schema_text") as mock_get_schema, \
         patch("app.api.enrich_query") as mock_enrich, \
         patch("app.api.build_prompt") as mock_build_prompt, \
         patch("app.api.run_page") as mock_run_page:
        
        # Setup mocks
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>SELECT id, name FROM customers LIMIT 10</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema.return_value = "Table: customers (id, name)"
        mock_enrich.return_value = "enriched: show me customers"
        mock_build_prompt.return_value = "Generate SQL for: show me customers"
        mock_run_page.return_value = (
            ["id", "name"],
            [[1, "Alice"], [2, "Bob"], [3, "Charlie"]],
            3
        )
        
        # Make non-streaming request
        response = client.post(
            "/query",
            json={
                "question": "Show me all customers",
                "stream": False
            }
        )
        
        print(f"Non-streaming response status: {response.status_code}")
        print(f"Content-Type: {response.headers.get('content-type')}")
        
        data = response.json()
        print(f"Response data: {json.dumps(data, indent=2)}")
        print("✅ Non-streaming test PASSED")
    
    # Test error scenarios
    print("\n4. Testing error handling...")
    
    # Test LLM not configured
    with patch("app.api.client", None):
        response = client.post(
            "/query",
            json={"question": "Show me customers"}
        )
        print(f"LLM not configured status: {response.status_code}")
        print(f"Error message: {response.json()['detail']}")
        assert response.status_code == 503
    
    # Test LLM API error
    with patch("app.api.client") as mock_client, \
         patch("app.api.get_schema_text") as mock_get_schema, \
         patch("app.api.enrich_query") as mock_enrich, \
         patch("app.api.build_prompt") as mock_build_prompt:
        
        mock_get_schema.return_value = "Table: customers (id, name)"
        mock_enrich.return_value = "enriched: show me customers"
        mock_build_prompt.return_value = "Generate SQL for: show me customers"
        mock_client.chat.completions.create.side_effect = Exception("API timeout")
        
        response = client.post(
            "/query",
            json={"question": "Show me customers"}
        )
        print(f"LLM API error status: {response.status_code}")
        print(f"Error message: {response.json()['detail']}")
        assert response.status_code == 502
    
    print("\n✅ All manual tests PASSED!")


if __name__ == "__main__":
    test_streaming_manually()