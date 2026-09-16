from unittest.mock import MagicMock
from src.llm.client import LLMClient


def test_groq_fallback_resilience(monkeypatch):
    client = LLMClient()
    client.provider = "groq"
    client.model = "openai/gpt-oss-120b"

    mock_client = MagicMock()
    # Primeira chamada falha com rate limit (429), segunda chamada funciona com Llama 3.3
    mock_success_msg = MagicMock()
    mock_success_msg.content = "Resposta do modelo de fallback"
    mock_success_msg.tool_calls = None

    mock_choice = MagicMock()
    mock_choice.message = mock_success_msg
    mock_response = MagicMock()
    mock_response.choices = [mock_choice]

    call_count = 0
    mock_raw = MagicMock()
    mock_raw.parse.return_value = mock_response
    mock_raw.headers = {"x-ratelimit-remaining-tokens": "7000", "x-ratelimit-reset-tokens": "1.0s"}

    def mock_create(**kwargs):
        nonlocal call_count
        call_count += 1
        if kwargs.get("model") == "openai/gpt-oss-120b":
            raise Exception("Rate limit reached: 429 Too Many Requests")
        return mock_raw

    mock_client.chat.completions.with_raw_response.create = mock_create
    mock_client.chat.completions.create = mock_create
    client.client = mock_client

    result = client.chat_completion(messages=[{"role": "user", "content": "olá"}])
    assert result["content"] == "Resposta do modelo de fallback"
    assert call_count >= 2
