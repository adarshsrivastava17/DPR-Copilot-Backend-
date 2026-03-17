"""Unified LLM client supporting OpenAI GPT and fallbacks."""
import asyncio
from openai import OpenAI
from config import get_settings

settings = get_settings()

_client = None


def get_llm_client():
    """Get a singleton OpenAI client."""
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.OPENAI_API_KEY)
    return _client


def generate_text_sync(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> str:
    """Generate text using the configured LLM (synchronous)."""
    client = get_llm_client()
    model = model or settings.OPENAI_MODEL

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


def generate_text_with_context_sync(
    system_prompt: str,
    context: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> str:
    """Generate text with a context injection for RAG (synchronous)."""
    client = get_llm_client()
    model = model or settings.OPENAI_MODEL

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": f"REFERENCE CONTEXT:\n{context}\n\n---\n\nTASK:\n{user_prompt}"},
    ]

    response = client.chat.completions.create(
        model=model,
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
    )

    return response.choices[0].message.content


# Async wrappers that run sync functions in thread pool
async def generate_text(
    system_prompt: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> str:
    """Async wrapper for generate_text_sync."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: generate_text_sync(system_prompt, user_prompt, model, temperature, max_tokens)
    )


async def generate_text_with_context(
    system_prompt: str,
    context: str,
    user_prompt: str,
    model: str | None = None,
    temperature: float = 0.3,
    max_tokens: int = 4000,
) -> str:
    """Async wrapper for generate_text_with_context_sync."""
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(
        None, lambda: generate_text_with_context_sync(system_prompt, context, user_prompt, model, temperature, max_tokens)
    )
