"""
Tests for database streaming functionality.
"""

import json
from unittest.mock import Mock, patch

import pytest

from shared.db import stream_query_results


class TestDatabaseStreaming:
    """Tests for the streaming database functionality."""

    @patch("shared.db.get_conn")
    @patch("shared.db.run_count")
    def test_stream_query_results_success(self, mock_run_count, mock_get_conn):
        """Test successful streaming of query results."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",), ("name",)]
        mock_run_count.return_value = 3
        
        # Mock fetchmany to return data in chunks
        call_count = 0
        def mock_fetchmany(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [(1, "John"), (2, "Jane")]
            elif call_count == 2:
                return [(3, "Bob")]
            else:
                return []
        
        mock_cursor.fetchmany = mock_fetchmany

        # Test streaming
        sql = "SELECT id, name FROM customers"
        page = 1
        page_size = 50
        
        result_chunks = list(stream_query_results(sql, page, page_size, chunk_size=2))
        
        # Combine chunks to get full JSON
        full_response = "".join(result_chunks)
        data = json.loads(full_response)
        
        # Assertions
        assert data["sql"] == sql
        assert data["columns"] == ["id", "name"]
        assert data["rows"] == [[1, "John"], [2, "Jane"], [3, "Bob"]]
        assert data["pagination"]["page"] == 1
        assert data["pagination"]["page_size"] == 50
        assert data["pagination"]["total_rows"] == 3
        assert data["pagination"]["total_pages"] == 1
        
        # Verify database operations
        mock_get_conn.assert_called_once()
        mock_conn.cursor.assert_called_once()
        mock_cursor.execute.assert_called_once_with("SELECT * FROM (SELECT id, name FROM customers) AS sub LIMIT 50 OFFSET 0")
        mock_cursor.close.assert_called_once()
        mock_conn.close.assert_called_once()

    @patch("shared.db.get_conn")
    def test_stream_query_results_database_error(self, mock_get_conn):
        """Test streaming with database error."""
        # Setup mock to raise exception
        mock_get_conn.side_effect = Exception("Database connection failed")
        
        # Test streaming with error
        sql = "SELECT id, name FROM customers"
        page = 1
        page_size = 50
        
        # Should raise the exception
        with pytest.raises(Exception, match="Database connection failed"):
            list(stream_query_results(sql, page, page_size))

    @patch("shared.db.get_conn")
    @patch("shared.db.run_count")
    def test_stream_query_results_empty_result(self, mock_run_count, mock_get_conn):
        """Test streaming with empty result set."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",), ("name",)]
        mock_run_count.return_value = 0
        mock_cursor.fetchmany.return_value = []  # No rows

        # Test streaming
        sql = "SELECT id, name FROM customers WHERE 1=0"
        page = 1
        page_size = 50
        
        result_chunks = list(stream_query_results(sql, page, page_size))
        
        # Combine chunks to get full JSON
        full_response = "".join(result_chunks)
        data = json.loads(full_response)
        
        # Assertions
        assert data["sql"] == sql
        assert data["columns"] == ["id", "name"]
        assert data["rows"] == []
        assert data["pagination"]["total_rows"] == 0
        assert data["pagination"]["total_pages"] == 0

    @patch("shared.db.get_conn")
    @patch("shared.db.run_count")
    def test_stream_query_results_pagination(self, mock_run_count, mock_get_conn):
        """Test streaming with pagination parameters."""
        # Setup mocks
        mock_conn = Mock()
        mock_cursor = Mock()
        mock_get_conn.return_value = mock_conn
        mock_conn.cursor.return_value = mock_cursor
        mock_cursor.description = [("id",), ("name",)]
        mock_run_count.return_value = 100  # Total rows
        
        # Mock fetchmany to return data once then empty
        call_count = 0
        def mock_fetchmany(size):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                return [(51, "User51"), (52, "User52")]  # Page 2 data
            else:
                return []  # No more data
        
        mock_cursor.fetchmany = mock_fetchmany

        # Test streaming page 2
        sql = "SELECT id, name FROM customers"
        page = 2
        page_size = 50
        
        result_chunks = list(stream_query_results(sql, page, page_size))
        
        # Combine chunks to get full JSON
        full_response = "".join(result_chunks)
        data = json.loads(full_response)
        
        # Assertions
        assert data["pagination"]["page"] == 2
        assert data["pagination"]["page_size"] == 50
        assert data["pagination"]["total_rows"] == 100
        assert data["pagination"]["total_pages"] == 2
        
        # Verify correct OFFSET was applied (page 2 = offset 50)
        expected_sql = "SELECT * FROM (SELECT id, name FROM customers) AS sub LIMIT 50 OFFSET 50"
        mock_cursor.execute.assert_called_once_with(expected_sql)