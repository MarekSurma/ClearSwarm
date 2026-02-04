"""Tests for LLM client module."""
import pytest
from unittest.mock import Mock, patch, MagicMock
from multi_agent.core.llm_client import LLMClient, OpenAILLMClient, MockLLMClient


class TestLLMClient:
    """Test cases for LLMClient abstract base class."""

    def test_llm_client_is_abstract(self):
        """Test that LLMClient cannot be instantiated directly."""
        with pytest.raises(TypeError):
            LLMClient()


class TestMockLLMClient:
    """Test cases for MockLLMClient."""

    @pytest.mark.asyncio
    async def test_mock_client_initialization(self):
        """Test MockLLMClient initialization."""
        mock_client = MockLLMClient()
        assert mock_client.call_count == 0
        assert mock_client.responses == []
        assert mock_client.call_history == []

    @pytest.mark.asyncio
    async def test_mock_client_with_canned_responses(self):
        """Test MockLLMClient returns canned responses."""
        responses = ["Response 1", "Response 2", "Response 3"]
        mock_client = MockLLMClient(responses=responses)

        # First call
        content1, model1 = await mock_client.generate_stream(
            messages=[{"role": "user", "content": "Test"}],
            model="test-model"
        )
        assert content1 == "Response 1"
        assert model1 == "test-model"
        assert mock_client.call_count == 1

        # Second call
        content2, model2 = await mock_client.generate_stream(
            messages=[{"role": "user", "content": "Test 2"}],
            model="test-model"
        )
        assert content2 == "Response 2"
        assert mock_client.call_count == 2

        # Third call
        content3, model3 = await mock_client.generate_stream(
            messages=[{"role": "user", "content": "Test 3"}],
            model="test-model"
        )
        assert content3 == "Response 3"
        assert mock_client.call_count == 3

    @pytest.mark.asyncio
    async def test_mock_client_default_response(self):
        """Test MockLLMClient returns default response when out of canned responses."""
        mock_client = MockLLMClient(responses=["Response 1"])

        # First call uses canned response
        content1, _ = await mock_client.generate_stream(
            messages=[{"role": "user", "content": "Test"}],
            model="test-model"
        )
        assert content1 == "Response 1"

        # Second call uses default response
        content2, _ = await mock_client.generate_stream(
            messages=[{"role": "user", "content": "Test 2"}],
            model="test-model"
        )
        assert content2 == "Mock response 2"

    @pytest.mark.asyncio
    async def test_mock_client_records_call_history(self):
        """Test MockLLMClient records call history."""
        mock_client = MockLLMClient()

        messages1 = [{"role": "user", "content": "Test 1"}]
        messages2 = [{"role": "user", "content": "Test 2"}]

        await mock_client.generate_stream(messages=messages1, model="model-1", temperature=0.5)
        await mock_client.generate_stream(messages=messages2, model="model-2", temperature=0.8)

        assert len(mock_client.call_history) == 2
        assert mock_client.call_history[0]["messages"] == messages1
        assert mock_client.call_history[0]["model"] == "model-1"
        assert mock_client.call_history[0]["temperature"] == 0.5
        assert mock_client.call_history[1]["messages"] == messages2
        assert mock_client.call_history[1]["model"] == "model-2"
        assert mock_client.call_history[1]["temperature"] == 0.8

    @pytest.mark.asyncio
    async def test_mock_client_reset(self):
        """Test MockLLMClient reset functionality."""
        mock_client = MockLLMClient(responses=["Response 1"])

        await mock_client.generate_stream(
            messages=[{"role": "user", "content": "Test"}],
            model="test-model"
        )
        assert mock_client.call_count == 1
        assert len(mock_client.call_history) == 1

        mock_client.reset()
        assert mock_client.call_count == 0
        assert mock_client.call_history == []


class TestOpenAILLMClient:
    """Test cases for OpenAILLMClient."""

    def test_openai_client_initialization_defaults(self):
        """Test OpenAILLMClient initialization with default config."""
        with patch('multi_agent.core.llm_client.Config') as mock_config:
            mock_config.OPENAI_API_KEY = "test-key"
            mock_config.OPENAI_API_BASE = "https://api.test.com"

            with patch('multi_agent.core.llm_client.OpenAI') as mock_openai:
                client = OpenAILLMClient()

                assert client.api_key == "test-key"
                assert client.base_url == "https://api.test.com"
                mock_openai.assert_called_once_with(
                    api_key="test-key",
                    base_url="https://api.test.com"
                )

    def test_openai_client_initialization_custom(self):
        """Test OpenAILLMClient initialization with custom parameters."""
        with patch('multi_agent.core.llm_client.OpenAI') as mock_openai:
            client = OpenAILLMClient(
                api_key="custom-key",
                base_url="https://custom.api.com"
            )

            assert client.api_key == "custom-key"
            assert client.base_url == "https://custom.api.com"
            mock_openai.assert_called_once_with(
                api_key="custom-key",
                base_url="https://custom.api.com"
            )

    @pytest.mark.asyncio
    async def test_openai_client_generate_stream(self):
        """Test OpenAILLMClient.generate_stream method."""
        # Create mock response chunks
        mock_chunk1 = Mock()
        mock_chunk1.choices = [Mock()]
        mock_chunk1.choices[0].delta = Mock()
        mock_chunk1.choices[0].delta.content = "Hello "
        mock_chunk1.model = "gpt-4"

        mock_chunk2 = Mock()
        mock_chunk2.choices = [Mock()]
        mock_chunk2.choices[0].delta = Mock()
        mock_chunk2.choices[0].delta.content = "world!"
        mock_chunk2.model = "gpt-4"

        # Mock OpenAI client
        mock_openai_instance = Mock()
        mock_stream = [mock_chunk1, mock_chunk2]
        mock_openai_instance.chat.completions.create.return_value = mock_stream

        with patch('multi_agent.core.llm_client.OpenAI') as mock_openai_class:
            mock_openai_class.return_value = mock_openai_instance

            client = OpenAILLMClient(api_key="test-key", base_url="https://api.test.com")

            # Mock print to capture streaming output
            with patch('builtins.print'):
                messages = [{"role": "user", "content": "Test"}]
                content, model = await client.generate_stream(
                    messages=messages,
                    model="gpt-4",
                    temperature=0.7
                )

                assert content == "Hello world!"
                assert model == "gpt-4"

                # Verify API was called correctly
                mock_openai_instance.chat.completions.create.assert_called_once_with(
                    model="gpt-4",
                    messages=messages,
                    temperature=0.7,
                    stream=True
                )

    @pytest.mark.asyncio
    async def test_openai_client_generate_stream_no_model_in_chunks(self):
        """Test OpenAILLMClient.generate_stream when chunks don't include model."""
        # Create mock response chunk without model attribute
        mock_chunk = Mock()
        mock_chunk.choices = [Mock()]
        mock_chunk.choices[0].delta = Mock()
        mock_chunk.choices[0].delta.content = "Test response"
        mock_chunk.model = None  # Simulate no model in chunk

        mock_openai_instance = Mock()
        mock_stream = [mock_chunk]
        mock_openai_instance.chat.completions.create.return_value = mock_stream

        with patch('multi_agent.core.llm_client.OpenAI') as mock_openai_class:
            mock_openai_class.return_value = mock_openai_instance

            client = OpenAILLMClient(api_key="test-key", base_url="https://api.test.com")

            with patch('builtins.print'):
                messages = [{"role": "user", "content": "Test"}]
                content, model = await client.generate_stream(
                    messages=messages,
                    model="gpt-4",
                    temperature=0.7
                )

                # Should fall back to requested model
                assert model == "gpt-4"
