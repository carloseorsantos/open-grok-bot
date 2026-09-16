import time
from unittest.mock import MagicMock
from src.llm.rate_limiter import GroqRateLimiter, parse_groq_duration
from src.llm.client import LLMClient


def test_parse_groq_duration():
    assert parse_groq_duration("3.435s") == 3.435
    assert parse_groq_duration("750ms") == 0.75
    assert parse_groq_duration("2m30s") == 150.0
    assert parse_groq_duration("1m") == 60.0
    assert parse_groq_duration("45s") == 45.0
    assert parse_groq_duration(None) == 0.0


def test_rate_limiter_header_update():
    limiter = GroqRateLimiter()
    headers = {
        "x-ratelimit-remaining-tokens": "5400",
        "x-ratelimit-limit-tokens": "8000",
        "x-ratelimit-reset-tokens": "4.2s",
        "x-ratelimit-remaining-requests": "995",
    }
    limiter.update_from_headers(headers)
    assert limiter.remaining_tokens == 5400
    assert limiter.limit_tokens == 8000
    assert limiter.remaining_requests == 995
    assert limiter.tokens_reset_at > time.time()


def test_rate_limiter_pre_flight_check(monkeypatch):
    limiter = GroqRateLimiter()
    limiter.remaining_tokens = 500
    limiter.tokens_reset_at = time.time() + 0.1

    slept_seconds = 0.0
    def mock_sleep(sec):
        nonlocal slept_seconds
        slept_seconds += sec

    monkeypatch.setattr(time, "sleep", mock_sleep)
    # Requer 1200 tokens, mas só tem 500 -> deve acionar pre_flight_check sleep
    limiter.pre_flight_check(estimated_tokens=1200)
    assert slept_seconds > 0.0


def test_rate_limiter_handle_429():
    limiter = GroqRateLimiter()
    mock_error = Exception("429 Too Many Requests")
    mock_resp = MagicMock()
    mock_resp.headers = {
        "retry-after": "2.5",
        "x-ratelimit-remaining-tokens": "0"
    }
    mock_error.response = mock_resp

    wait_time = limiter.handle_rate_limit_error(mock_error)
    assert wait_time >= 2.5


def test_multi_key_rotation(monkeypatch):
    from src.config import settings
    monkeypatch.setattr(settings, "GROQ_API_KEY", "key_alpha,key_beta,key_gamma")
    client = LLMClient()
    assert len(client.groq_keys) == 3
    assert client.current_key_idx == 0

    client._rotate_groq_key()
    assert client.current_key_idx == 1

    client._rotate_groq_key()
    assert client.current_key_idx == 2

    client._rotate_groq_key()
    assert client.current_key_idx == 0
