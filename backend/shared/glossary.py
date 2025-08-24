"""
Glossary and enrichment utilities for RAG (Retrieval-Augmented Generation).
"""

from typing import Any, Dict, List

GLOSSARY: List[Dict[str, Any]] = [
    {
        "term": "membership holder",
        "hint": "customers.is_member = TRUE",
        "applies_to": "customers,ticket_sales",
    },
    {
        "term": "active sales",
        "hint": "status = 'active' OR payment_status = 'paid'",
        "applies_to": "ticket_sales,merch_orders",
    },
    {
        "term": "ticketing",
        "hint": "use ticket_sales table; date column often sale_date",
        "applies_to": "ticket_sales",
    },
    {
        "term": "merchandise",
        "hint": "use merch_orders with product_category, revenue",
        "applies_to": "merch_orders",
    },
]


def enrich_with_glossary(user_query: str) -> str:
    """
    Enrich a user query with glossary hints if glossary terms are present.
    Args:
        user_query (str): The user's question.
    Returns:
        str: The enriched query with hints appended if any terms matched.
    """
    lower = user_query.lower()
    hints = [f"- {g['term']}: {g['hint']}" for g in GLOSSARY if g["term"] in lower]
    return user_query + ("\n\nHINTS:\n" + "\n".join(hints) if hints else "")
