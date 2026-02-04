"""
LLM Client interface and implementations.
Provides abstraction layer for LLM API calls with dependency injection support.
"""
from abc import ABC, abstractmethod
from typing import List, Dict, Any, Tuple, Optional
import asyncio
import threading
from datetime import datetime
from openai import OpenAI

from .config import Config


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
        temperature: float = 0.7
    ) -> Tuple[str, str]:
        """
        Generate a streaming response from the LLM.

        Args:
            messages: List of conversation messages
            model: Model identifier
            temperature: Sampling temperature

        Returns:
            Tuple of (response_content, model_used)
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
        temperature: float = 0.7
    ) -> Tuple[str, str]:
        """
        Generate a streaming response from OpenAI API.

        Args:
            messages: List of conversation messages
            model: Model identifier
            temperature: Sampling temperature

        Returns:
            Tuple of (response_content, model_used)
        """
        shutdown_event = get_shutdown_event()

        def _sync_stream_call():
            stream = self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=True
            )

            # Collect streamed response
            response_content = ""
            response_model = None

            try:
                for chunk in stream:
                    # Check for shutdown request
                    if shutdown_event.is_set():
                        print("\n[LLM streaming interrupted]", flush=True)
                        stream.close()
                        break

                    if chunk.choices and len(chunk.choices) > 0:
                        delta = chunk.choices[0].delta
                        if hasattr(delta, 'content') and delta.content:
                            content = delta.content
                            response_content += content
                            # Only print if content has non-whitespace characters
                            if content.strip():
                                print(content, end='', flush=True)

                    # Save model info from first chunk
                    if not response_model and hasattr(chunk, 'model'):
                        response_model = chunk.model

                print()  # New line after streaming
            except Exception as e:
                if shutdown_event.is_set():
                    print("\n[LLM streaming interrupted]", flush=True)
                else:
                    raise

            return response_content, response_model

        # Run in thread pool to avoid blocking event loop
        response_content, response_model = await asyncio.to_thread(_sync_stream_call)

        return response_content, response_model or model


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
        temperature: float = 0.7
    ) -> Tuple[str, str]:
        """
        Return a mock response.

        Args:
            messages: List of conversation messages
            model: Model identifier
            temperature: Sampling temperature

        Returns:
            Tuple of (response_content, model_used)
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
        return response, model

    def reset(self):
        """Reset mock state."""
        self.call_count = 0
        self.call_history = []
