"""
RAG enrichment pipeline for text2sql agent.
Supports glossary, schema, and (future) semantic search.
"""

from shared.glossary import enrich_with_glossary


# Placeholder for semantic search (to be implemented with embeddings/vector DB)
def semantic_search_enrich(user_query: str) -> str:
    return ""  # Semantic search stub


def enrich_query(user_query: str) -> str:
    """
    Enrich user query with RAG sources: glossary, schema, semantic search, etc.
    Args:
        user_query (str): The user's question.
    Returns:
        str: Enriched query with appended context/hints.
    """
    enriched = user_query
    glossary_hints = enrich_with_glossary(user_query)
    if glossary_hints != user_query:
        enriched = glossary_hints
    # Optionally add semantic search results
    sem = semantic_search_enrich(user_query)
    if sem:
        enriched += f"\n\nSEMANTIC HINTS:\n{sem}"
    return enriched


# For prompt construction


def build_prompt(user_query: str, schema: str, enriched: str) -> str:
    return f"""
<schema>\n{schema}\n</schema>\n\nUser question:\n{enriched}\n\nRules: Only a single SELECT. Use public schema tables. Use GROUP BY when totals are asked.\nReturn:\n<sql> ... </sql>\n"""
