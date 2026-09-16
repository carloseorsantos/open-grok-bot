import pytest
from pathlib import Path
from unittest.mock import MagicMock
from src.tools.audio import transcribe_audio
from src.llm.client import llm_client


def test_transcribe_audio_missing_file():
    res = transcribe_audio("arquivo_que_nao_existe_12345.ogg")
    assert "Erro: Arquivo de áudio não encontrado" in res


def test_transcribe_audio_success(tmp_path, monkeypatch):
    # Cria arquivo fictício
    dummy_audio = tmp_path / "test_audio.ogg"
    dummy_audio.write_bytes(b"dummy audio content")

    mock_response = MagicMock()
    mock_response.text = "Olá Open Grok Bot, pesquise as notícias de hoje."

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = mock_response

    monkeypatch.setattr(llm_client, "client", mock_client)

    result = transcribe_audio(str(dummy_audio), language="pt")
    assert result == "Olá Open Grok Bot, pesquise as notícias de hoje."
    mock_client.audio.transcriptions.create.assert_called_once()


def test_transcribe_audio_dict_response(tmp_path, monkeypatch):
    dummy_audio = tmp_path / "voice_sample.mp3"
    dummy_audio.write_bytes(b"another dummy audio")

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.return_value = {
        "text": "Cotação do Bitcoin agora"
    }
    monkeypatch.setattr(llm_client, "client", mock_client)

    result = transcribe_audio(str(dummy_audio))
    assert result == "Cotação do Bitcoin agora"


def test_transcribe_audio_api_error(tmp_path, monkeypatch):
    dummy_audio = tmp_path / "error_audio.ogg"
    dummy_audio.write_bytes(b"corrupted audio")

    mock_client = MagicMock()
    mock_client.audio.transcriptions.create.side_effect = Exception("Groq Whisper API connection failed")
    monkeypatch.setattr(llm_client, "client", mock_client)

    result = transcribe_audio(str(dummy_audio))
    assert "Erro ao transcrever áudio" in result
    assert "Groq Whisper API connection failed" in result
