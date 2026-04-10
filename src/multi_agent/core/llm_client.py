"""
LLM Client interface and implementations.
Provides abstraction layer for LLM API calls with dependency injection support.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional, Callable
import asyncio
import logging
import threading
import time
from datetime import datetime
from openai import OpenAI

logger = logging.getLogger(__name__)

from .config import Config

# How often (in seconds) to save partial streamed content to the log file.
# This makes streaming progress visible to the web frontend between polls.
STREAM_LOG_INTERVAL_SECONDS = 1.0


# Global flag for graceful shutdown
_shutdown_event: Optional[threading.Event] = None


def get_shutdown_event() -> threading.Event:
    """Get or create the global shutdown event."""
    global _shutdown_event
    if _shutdown_event is None:
        _shutdown_event = threading.Event()
    return _shutdown_event


def request_shutdown():
    """Signal all LLM clients to stop."""
    get_shutdown_event().set()


def reset_shutdown():
    """Reset shutdown flag for new operations."""
    get_shutdown_event().clear()


def is_shutdown_requested() -> bool:
    """Check if shutdown was requested."""
    return get_shutdown_event().is_set()


class LLMClient(ABC):
    """Abstract base class for LLM clients."""

    @abstractmethod
    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        on_stream_update: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Tuple[str, str, Optional[str]]:
        """
        Generate a streaming response from the LLM.

        Args:
            messages: List of conversation messages
            model: Model identifier
            temperature: Sampling temperature
            on_stream_update: Optional callback called periodically with partial content during streaming
            cancel_event: Optional per-agent cancellation event; checked alongside global shutdown

        Returns:
            Tuple of (response_content, model_used, finish_reason)
        """
        pass


class OpenAILLMClient(LLMClient):
    """OpenAI-compatible LLM client implementation."""

    def __init__(self, api_key: str = None, base_url: str = None):
        """
        Initialize OpenAI client.

        Args:
            api_key: API key (defaults to Config.OPENAI_API_KEY)
            base_url: Base URL (defaults to Config.OPENAI_API_BASE)
        """
        self.api_key = api_key or Config.OPENAI_API_KEY
        self.base_url = base_url or Config.OPENAI_API_BASE

        self.client = OpenAI(
            api_key=self.api_key,
            base_url=self.base_url
        )

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        on_stream_update: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Tuple[str, str]:
        """
        Generate a streaming response from OpenAI API.

        Args:
            messages: List of conversation messages
            model: Model identifier
            temperature: Sampling temperature
            on_stream_update: Optional callback called periodically with partial content during streaming
            cancel_event: Optional per-agent cancellation event; checked alongside global shutdown

        Returns:
            Tuple of (response_content, model_used)
        """
        shutdown_event = get_shutdown_event()

        def _should_stop():
            """Check if streaming should stop (global shutdown or per-agent cancel)."""
            return shutdown_event.is_set() or (cancel_event is not None and cancel_event.is_set())

        def _sync_stream_call():
            # Check cancellation before starting the HTTP request
            if _should_stop():
                return "", None, "cancelled"

            stream_start_time = time.time()

            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=Config.OPENAI_MAX_TOKENS,
                stream=True,
                timeout=Config.OPENAI_API_TIMEOUT
            )

            # Collect streamed response
            response_content = ""
            response_model = None
            finish_reason = None
            last_update_time = time.time()
            chunk_count = 0

            try:
                for chunk in stream:
                    chunk_count += 1
                    # Check for shutdown or per-agent cancellation
                    if _should_stop():
                        stream.close()
                        finish_reason = "cancelled"
                        break

                    if chunk.choices and len(chunk.choices) > 0:
                        choice = chunk.choices[0]
                        delta = choice.delta
                        if hasattr(delta, 'content') and delta.content:
                            content = delta.content
                            response_content += content

                        # Track finish reason from the final chunk
                        if hasattr(choice, 'finish_reason') and choice.finish_reason:
                            finish_reason = choice.finish_reason

                    # Save model info from first chunk
                    if not response_model and hasattr(chunk, 'model'):
                        response_model = chunk.model

                    # Periodic streaming update for live log monitoring
                    now = time.time()
                    if on_stream_update and response_content and (now - last_update_time) >= STREAM_LOG_INTERVAL_SECONDS:
                        on_stream_update(response_content)
                        last_update_time = now

            except Exception as e:
                if _should_stop():
                    finish_reason = "cancelled"
                else:
                    elapsed = time.time() - stream_start_time
                    logger.error(
                        "LLM streaming error after %.1fs, %d chunks, %d chars: %s",
                        elapsed, chunk_count, len(response_content), str(e)
                    )
                    print(f"[LLM ERROR] Streaming failed after {elapsed:.1f}s, "
                          f"{chunk_count} chunks, {len(response_content)} chars: {e}",
                          flush=True)
                    raise

            elapsed = time.time() - stream_start_time
            print(f"[LLM STREAM] model={response_model or model} "
                  f"finish_reason={finish_reason} "
                  f"chars={len(response_content)} chunks={chunk_count} "
                  f"time={elapsed:.1f}s max_tokens={Config.OPENAI_MAX_TOKENS}",
                  flush=True)

            if finish_reason == "length":
                print(f"[LLM WARNING] Response TRUNCATED! finish_reason=length, "
                      f"chars={len(response_content)}, max_tokens={Config.OPENAI_MAX_TOKENS}",
                      flush=True)
            elif finish_reason is None and response_content:
                print(f"[LLM WARNING] No finish_reason received! "
                      f"Response may be incomplete. chars={len(response_content)}",
                      flush=True)

            return response_content, response_model, finish_reason

        # Run in thread pool to avoid blocking event loop
        response_content, response_model, finish_reason = await asyncio.to_thread(_sync_stream_call)

        return response_content, response_model or model, finish_reason


class MockLLMClient(LLMClient):
    """Mock LLM client for testing."""

    def __init__(self, responses: List[str] = None):
        """
        Initialize mock client.

        Args:
            responses: List of canned responses to return sequentially
        """
        self.responses = responses or []
        self.call_count = 0
        self.call_history: List[Dict[str, Any]] = []

    async def generate_stream(
        self,
        messages: List[Dict[str, str]],
        model: str,
        temperature: float = 0.7,
        on_stream_update: Optional[Callable[[str], None]] = None,
        cancel_event: Optional[threading.Event] = None
    ) -> Tuple[str, str, Optional[str]]:
        """
        Return a mock response.

        Args:
            messages: List of conversation messages
            model: Model identifier
            temperature: Sampling temperature
            on_stream_update: Optional callback (unused in mock)
            cancel_event: Optional cancellation event (unused in mock)

        Returns:
            Tuple of (response_content, model_used, finish_reason)
        """
        # Record call
        self.call_history.append({
            'messages': messages.copy(),
            'model': model,
            'temperature': temperature,
            'timestamp': datetime.now().isoformat()
        })

        # Return canned response or default
        if self.call_count < len(self.responses):
            response = self.responses[self.call_count]
        else:
            response = f"Mock response {self.call_count + 1}"

        self.call_count += 1
        return response, model, "stop"

    def reset(self):
        """Reset mock state."""
        self.call_count = 0
        self.call_history = []
