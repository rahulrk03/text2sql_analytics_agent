"""
Database utility functions for connecting to PostgreSQL and running paginated queries.
"""

import os
import json
from typing import Iterator, Tuple

import psycopg2

DB = {
    "host": os.getenv("DB_HOST"),
    "port": int(os.getenv("DB_PORT", "5432")),
    "dbname": os.getenv("DB_NAME"),
    "user": os.getenv("DB_USER"),
    "password": os.getenv("DB_PASS"),
}


def get_conn():
    """
    Create a new psycopg2 connection using environment variables.
    Returns:
        psycopg2.extensions.connection: Database connection object.
    """
    return psycopg2.connect(**DB)


# separate alias used by lambda to avoid circular import surprises
get_psycopg_conn = get_conn


def run_count(conn, sql: str) -> int:
    """
    Count the number of rows returned by a SQL query.
    Args:
        conn: psycopg2 connection.
        sql (str): SQL SELECT query.
    Returns:
        int: Number of rows.
    """
    cur = conn.cursor()
    cur.execute(f"SELECT COUNT(1) FROM ({sql}) AS sub")
    n = int(cur.fetchone()[0])
    cur.close()
    return n


def run_page(sql: str, page: int, page_size: int):
    """
    Run a paginated SQL query and return columns, rows, and total count.
    Args:
        sql (str): SQL SELECT query.
        page (int): Page number (1-based).
        page_size (int): Number of rows per page.
    Returns:
        tuple: (columns, rows, total_rows)
    """
    offset = (page - 1) * page_size
    paginated = f"SELECT * FROM ({sql}) AS sub LIMIT {page_size} OFFSET {offset}"
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(paginated)
    rows = cur.fetchall()
    cols = [d[0] for d in cur.description]
    total = run_count(conn, sql)
    cur.close()
    conn.close()
    return cols, rows, total


def stream_query_results(sql: str, page: int, page_size: int, chunk_size: int = 100) -> Iterator[str]:
    """
    Stream SQL query results as JSON chunks for the specified page.
    Yields JSON fragments that can be concatenated to form a complete response.
    
    Args:
        sql (str): SQL SELECT query.
        page (int): Page number (1-based).
        page_size (int): Number of rows per page.
        chunk_size (int): Number of rows to fetch at a time for streaming.
    
    Yields:
        str: JSON string fragments for streaming response.
    """
    offset = (page - 1) * page_size
    paginated = f"SELECT * FROM ({sql}) AS sub LIMIT {page_size} OFFSET {offset}"
    
    conn = None
    cur = None
    try:
        conn = get_conn()
        cur = conn.cursor()
        cur.execute(paginated)
        
        # Get column names
        cols = [d[0] for d in cur.description]
        
        # Get total count
        total = run_count(conn, sql)
        
        # Start JSON response
        yield '{"sql": ' + json.dumps(sql) + ', "columns": ' + json.dumps(cols) + ', "rows": ['
        
        first_row = True
        rows_count = 0
        
        while True:
            rows = cur.fetchmany(chunk_size)
            if not rows:
                break
                
            for row in rows:
                if not first_row:
                    yield ","
                yield json.dumps(list(row))
                first_row = False
                rows_count += 1
        
        # Close rows array and add pagination info
        yield '], "pagination": {'
        yield f'"page": {page}, "page_size": {page_size}, "total_rows": {total}, '
        yield f'"total_pages": {(total + page_size - 1) // page_size}'
        yield '}}'
        
    finally:
        if cur:
            cur.close()
        if conn:
            conn.close()
