import pytest
from unittest.mock import patch, MagicMock
from agent_scorecard.llm import LLMClient


class TestLLMClient:
    def test_init_defaults(self) -> None:
        client = LLMClient()
        assert client.model == "gpt-4o"
        assert client.api_key is None

    def test_init_config(self) -> None:
        config = {"model": "claude-3", "api_key": "sk-123"}
        client = LLMClient(config)
        assert client.model == "claude-3"
        assert client.api_key == "sk-123"

    def test_generate_success(self) -> None:
        with patch("agent_scorecard.llm.litellm") as mock_litellm:
            mock_response = MagicMock()
            mock_response.choices = [
                MagicMock(message=MagicMock(content="Fixed code"))
            ]
            mock_litellm.completion.return_value = mock_response

            client = LLMClient()
            result = client.generate("system", "user")

            assert result == "Fixed code"
            mock_litellm.completion.assert_called_once()
            args, kwargs = mock_litellm.completion.call_args
            assert kwargs["model"] == "gpt-4o"
            assert kwargs["messages"] == [
                {"role": "system", "content": "system"},
                {"role": "user", "content": "user"},
            ]

    def test_generate_missing_litellm(self) -> None:
        with patch("agent_scorecard.llm.litellm", None):
            client = LLMClient()
            with pytest.raises(ImportError, match="litellm is required"):
                client.generate("sys", "user")

    def test_generate_error_handling(self) -> None:
        with patch("agent_scorecard.llm.litellm") as mock_litellm:
            mock_litellm.completion.side_effect = Exception("API Error")

            client = LLMClient()
            # It should catch exception and return empty string, printing to stderr
            result = client.generate("sys", "user")
            assert result == ""
