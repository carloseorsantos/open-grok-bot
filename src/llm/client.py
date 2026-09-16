import json
import logging
from typing import Any, Callable, Optional
from openai import OpenAI
from src.config import settings

logger = logging.getLogger("OpenGrokBot.LLM")


class LLMClient:
    """
    Cliente universal de LLM compatível com a API OpenAI (Groq, Ollama, OpenAI, xAI).
    Oferece suporte a Tool/Function Calling e streaming.
    """
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.client = self._init_client()
        self.model = self._get_model_name()

    def _init_client(self) -> Optional[OpenAI]:
        try:
            if self.provider == "groq":
                if not settings.GROQ_API_KEY:
                    logger.warning("GROQ_API_KEY não configurada no .env. Obtenha uma grátis em https://console.groq.com")
                return OpenAI(
                    api_key=settings.GROQ_API_KEY or "dummy_key",
                    base_url="https://api.groq.com/openai/v1"
                )
            elif self.provider == "ollama":
                return OpenAI(
                    api_key="ollama",
                    base_url=settings.OLLAMA_BASE_URL
                )
            else:
                return OpenAI(
                    api_key=settings.OPENAI_API_KEY or "dummy_key",
                    base_url=settings.OPENAI_BASE_URL
                )
        except Exception as e:
            logger.error(f"Erro ao inicializar cliente LLM ({self.provider}): {e}")
            return None

    def _get_model_name(self) -> str:
        if self.provider == "groq":
            return settings.GROQ_MODEL
        elif self.provider == "ollama":
            return settings.OLLAMA_MODEL
        return settings.OPENAI_MODEL

    def chat_completion(
        self,
        messages: list[dict],
        tools: Optional[list[dict]] = None,
        temperature: float = 0.7
    ) -> dict:
        """
        Executa uma requisição de chat completion com suporte a tools.
        Retorna dicionário com 'content' e 'tool_calls'.
        """
        if not self.client:
            return {
                "content": "Erro: Cliente de IA não configurado.",
                "tool_calls": None
            }

        # Verificação amigável de chave Groq
        if self.provider == "groq" and (not settings.GROQ_API_KEY or settings.GROQ_API_KEY == "gsk_your_groq_key_here"):
            return {
                "content": (
                    "⚠️ **Chave da Groq não configurada!**\n\n"
                    "Para usar o modelo **Llama 3.3 70B** de graça e sem custos:\n"
                    "1. Acesse https://console.groq.com e crie uma conta gratuita (não precisa de cartão).\n"
                    "2. Crie uma API Key e cole no arquivo `.env` na variável `GROQ_API_KEY=gsk_...`\n\n"
                    "*Dica: Você também pode usar Ollama local configurando `LLM_PROVIDER=ollama` no `.env`.*"
                ),
                "tool_calls": None
            }

        # Lista de modelos a tentar em ordem
        candidate_models = [self.model]
        if self.provider == "groq":
            fallback_models = ["openai/gpt-oss-20b", "groq/compound-mini", "groq/compound"]
            for fm in fallback_models:
                if fm not in candidate_models:
                    candidate_models.append(fm)

        last_error = ""
        for current_model in candidate_models:
            try:
                kwargs = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                response = self.client.chat.completions.create(**kwargs)
                message = response.choices[0].message

                parsed_tool_calls = []
                if message.tool_calls:
                    for tc in message.tool_calls:
                        parsed_tool_calls.append({
                            "id": tc.id,
                            "name": tc.function.name,
                            "arguments": json.loads(tc.function.arguments) if tc.function.arguments else {}
                        })

                return {
                    "content": message.content or "",
                    "tool_calls": parsed_tool_calls if parsed_tool_calls else None,
                    "raw_message": message
                }
            except Exception as e:
                last_error = str(e)
                logger.warning(f"Erro com o modelo {current_model}: {last_error}. Tentando fallback...")

        return {
            "content": f"Erro na chamada do modelo ({self.provider}/{self.model}): {last_error}",
            "tool_calls": None
        }


llm_client = LLMClient()
