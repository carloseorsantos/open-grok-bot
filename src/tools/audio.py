import logging
from pathlib import Path
from typing import Optional, Union
from src.config import settings
from src.llm.client import llm_client

logger = logging.getLogger("OpenGrokBot.Audio")


def transcribe_audio(
    file_path: Union[str, Path],
    language: Optional[str] = "pt",
    prompt: Optional[str] = None
) -> str:
    """
    Transcreve um arquivo de áudio para texto usando Groq Whisper (whisper-large-v3-turbo).
    Suporta formatos comuns de áudio: .ogg, .mp3, .m4a, .wav, .webm, .flac.
    Custo: 100% gratuito (dentro da cota de 7.200s de áudio/hora da Groq).
    """
    path = Path(file_path)
    if not path.exists():
        return f"Erro: Arquivo de áudio não encontrado em '{file_path}'"

    if not llm_client.client:
        return "Erro: Cliente de IA não configurado."

    try:
        model = getattr(settings, "GROQ_WHISPER_MODEL", "whisper-large-v3-turbo")
        with open(path, "rb") as f:
            kwargs = {
                "model": model,
                "file": (path.name, f.read())
            }
            if language:
                kwargs["language"] = language
            if prompt:
                kwargs["prompt"] = prompt

            logger.info(f"Enviando áudio '{path.name}' para transcrição no modelo {model}...")
            transcription = llm_client.client.audio.transcriptions.create(**kwargs)

            # Compatibilidade com retorno objeto ou dicionário
            if hasattr(transcription, "text"):
                text = transcription.text
            elif isinstance(transcription, dict):
                text = transcription.get("text", "")
            else:
                text = str(transcription)

            return text.strip()
    except Exception as e:
        logger.error(f"Erro ao transcrever áudio com Whisper: {e}")
        return f"Erro ao transcrever áudio: {str(e)}"
