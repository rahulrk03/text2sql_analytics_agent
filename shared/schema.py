"""
Schema extraction utility for describing the public schema of the database.
"""

from shared.db import get_conn


def get_schema_text() -> str:
    """
    Get a text description of all tables and columns in the public schema.
    Returns:
        str: Human-readable schema description.
    """
    conn = get_conn()
    cur = conn.cursor()
    cur.execute(
        """
        SELECT table_schema, table_name, column_name, data_type
        FROM information_schema.columns
        WHERE table_schema = 'public'
        ORDER BY table_schema, table_name, ordinal_position;
        """
    )
    rows = cur.fetchall()
    cur.close()
    conn.close()
    lines, curtbl = [], None
    for schema, table, col, dtype in rows:
        if curtbl != (schema, table):
            curtbl = (schema, table)
            lines.append(f"\nTable {schema}.{table}:")
        lines.append(f"  - {col} ({dtype})")
    return "\n".join(lines).strip()
