"""
Tests for the API endpoints with streaming support and improved error handling.
"""

import json
from unittest.mock import Mock, patch

import pytest
from fastapi.testclient import TestClient

from app.api import app


@pytest.fixture
def client():
    """FastAPI test client fixture."""
    return TestClient(app)


class TestQueryEndpoint:
    """Tests for the /query endpoint."""

    def test_health_endpoint(self, client):
        """Test the health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json() == {"ok": True}

    def test_query_missing_question(self, client):
        """Test query endpoint with missing question field."""
        response = client.post("/query", json={})
        assert response.status_code == 422  # Validation error

    def test_query_llm_not_configured(self, client):
        """Test query endpoint when LLM is not configured."""
        with patch("app.api.client", None):
            response = client.post(
                "/query",
                json={"question": "What are the customers?"},
            )
            assert response.status_code == 503
            assert "LLM service not configured" in response.json()["detail"]

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    def test_query_llm_api_error(
        self,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test query endpoint with LLM API error."""
        # Setup mocks
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        mock_client.chat.completions.create.side_effect = Exception("API error")

        # Make request
        response = client.post(
            "/query",
            json={"question": "What are the customers?"},
        )

        # Assertions
        assert response.status_code == 502
        assert "LLM service error" in response.json()["detail"]

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    def test_query_invalid_sql_format(
        self,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test query endpoint with non-SELECT SQL."""
        # Setup mocks to return non-SELECT SQL
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>UPDATE customers SET name = 'test'</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"

        # Make request
        response = client.post(
            "/query",
            json={"question": "Update customer names"},
        )

        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Unsafe or invalid SQL generated"

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    def test_query_unsafe_sql(
        self,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test query endpoint with unsafe SQL."""
        # Setup mocks to return unsafe SQL
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>DELETE FROM customers</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"

        # Make request
        response = client.post(
            "/query",
            json={"question": "Delete all customers"},
        )

        # Assertions
        assert response.status_code == 400
        assert response.json()["detail"] == "Unsafe or invalid SQL generated"

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    @patch("app.api.run_page")
    def test_query_non_streaming_success(
        self,
        mock_run_page,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test successful non-streaming query."""
        # Setup mocks
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>SELECT * FROM customers</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        mock_run_page.return_value = (
            ["id", "name"],
            [[1, "John"], [2, "Jane"]],
            2
        )

        # Make request with stream=False
        response = client.post(
            "/query",
            json={"question": "Show me customers", "stream": False},
        )

        # Assertions
        assert response.status_code == 200
        data = response.json()
        assert data["sql"] == "SELECT * FROM customers"
        assert data["columns"] == ["id", "name"]
        assert data["rows"] == [[1, "John"], [2, "Jane"]]
        assert data["pagination"]["total_rows"] == 2

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    @patch("app.api.run_page")
    def test_query_database_connection_error(
        self,
        mock_run_page,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test query endpoint with database connection error."""
        # Setup mocks
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>SELECT * FROM customers</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        mock_run_page.side_effect = Exception("connection timeout")

        # Make request with stream=False
        response = client.post(
            "/query",
            json={"question": "Show me customers", "stream": False},
        )

        # Assertions
        assert response.status_code == 503
        assert "Database error" in response.json()["detail"]
        assert "connection timeout" in response.json()["detail"]

    @patch("app.api.client")
    @patch("app.api.get_schema_text")
    @patch("app.api.enrich_query")
    @patch("app.api.build_prompt")
    @patch("app.api.stream_query_results")
    def test_query_streaming_success(
        self,
        mock_stream_query_results,
        mock_build_prompt,
        mock_enrich_query,
        mock_get_schema_text,
        mock_client,
        client,
    ):
        """Test successful streaming query."""
        # Setup mocks
        mock_response = Mock()
        mock_response.choices = [Mock()]
        mock_response.choices[0].message.content = "<sql>SELECT * FROM customers</sql>"
        mock_client.chat.completions.create.return_value = mock_response
        mock_get_schema_text.return_value = "Schema info"
        mock_enrich_query.return_value = "enriched query"
        mock_build_prompt.return_value = "built prompt"
        
        # Mock streaming response
        def mock_generator():
            yield '{"sql": "SELECT * FROM customers", "columns": ["id", "name"], "rows": ['
            yield '[1, "John"]'
            yield ', [2, "Jane"]'
            yield '], "pagination": {"page": 1, "page_size": 50, "total_rows": 2, "total_pages": 1}}'
        
        mock_stream_query_results.return_value = mock_generator()

        # Make request with stream=True (default)
        response = client.post(
            "/query",
            json={"question": "Show me customers"},
        )

        # Assertions
        assert response.status_code == 200
        assert "application/json" in response.headers["content-type"]
        
        # Read streaming content
        content = b"".join(response.iter_bytes()).decode()
        data = json.loads(content)
        assert data["sql"] == "SELECT * FROM customers"
        assert data["columns"] == ["id", "name"]
        assert data["rows"] == [[1, "John"], [2, "Jane"]]