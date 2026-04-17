import os
from crewai import LLM
from backend.config import settings


def get_oci_llm() -> LLM:
    """
    OCI GenAI LLM for CrewAI via litellm OpenAI-compatible endpoint.
    Falls back to OCIGenAIDirectLLM if this has issues.
    """
    return LLM(
        model="openai/cohere.command-r-plus",
        base_url=settings.oci_genai_endpoint,
        api_key=settings.oci_genai_api_key,
        temperature=0.2,
        max_tokens=4096,
        custom_llm_provider="openai",
    )


def get_embedding_fn():
    """
    Returns a callable that generates embeddings using the in-database
    ONNX model loaded into ADB 26ai. No external API call needed.
    Used for query-side embedding during semantic search.
    """
    import oracledb
    from backend.db.connection import get_connection

    def embed_text(text: str) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TO_VECTOR(DBMS_VECTOR.UTL_TO_EMBEDDING(
                :text_input,
                JSON('{"provider":"database","model":"ALL_MINILM_L12_V2"}')
            )) FROM DUAL
            """,
            {"text_input": text},
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else []

    return embed_text
