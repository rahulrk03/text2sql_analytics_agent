"""
SQL safety and extraction utilities.
"""

import re

WRITE_RE = re.compile(
    r"\b(INSERT|UPDATE|DELETE|ALTER|DROP|TRUNCATE|MERGE|CALL|COPY|GRANT|REVOKE)\b", re.I
)


def is_safe(sql: str) -> bool:
    """
    Check if a SQL query is read-only (safe for execution).
    Args:
        sql (str): SQL query.
    Returns:
        bool: True if safe, False if it contains write operations.
    """
    return not WRITE_RE.search(sql)


def extract_sql(text_: str) -> str:
    """
    Extract SQL code from <sql>...</sql> tags in a string.
    Args:
        text_ (str): Text containing SQL in tags.
    Returns:
        str: Extracted SQL or original text if tags not found.
    """
    m = re.search(r"<sql>([\s\S]*?)</sql>", text_, re.I)
    return (m.group(1) if m else text_).strip()
