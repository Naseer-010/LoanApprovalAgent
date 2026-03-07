"""
Centralized LLM Factory — single place to swap models for all three pillars.

Uses HuggingFaceEndpoint (HF Inference API) by default.
To switch to local inference, replace HuggingFaceEndpoint with HuggingFacePipeline.
"""

from functools import lru_cache

from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint

from app.config import settings


def _create_llm(model_id: str) -> ChatHuggingFace:
    """Create a ChatHuggingFace instance wrapping a HuggingFaceEndpoint."""
    endpoint = HuggingFaceEndpoint(
        repo_id=model_id,
        huggingfacehub_api_token=settings.HUGGINGFACEHUB_API_TOKEN,
        max_new_tokens=settings.LLM_MAX_NEW_TOKENS,
        temperature=settings.LLM_TEMPERATURE,
        task="text-generation",
    )
    return ChatHuggingFace(llm=endpoint)


@lru_cache(maxsize=1)
def get_ingestor_llm() -> ChatHuggingFace:
    """LLM for document extraction and analysis (Pillar 1)."""
    return _create_llm(settings.INGESTOR_MODEL)


@lru_cache(maxsize=1)
def get_research_llm() -> ChatHuggingFace:
    """LLM for research agent reasoning (Pillar 2)."""
    return _create_llm(settings.RESEARCH_MODEL)


@lru_cache(maxsize=1)
def get_recommendation_llm() -> ChatHuggingFace:
    """LLM for credit recommendation (Pillar 3)."""
    return _create_llm(settings.RECOMMENDATION_MODEL)
