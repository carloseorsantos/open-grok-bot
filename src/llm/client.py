import json
import logging
import time
from typing import Any, Callable, List, Optional
from openai import OpenAI
from src.config import settings
from src.llm.rate_limiter import rate_limiter

logger = logging.getLogger("OpenGrokBot.LLM")


class LLMClient:
    """
    Cliente universal de LLM compatível com a API OpenAI (Groq, Ollama, OpenAI, xAI).
    Oferece suporte a Tool/Function Calling, Rate Limit Proativo, e rotação de chaves.
    """
    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self.groq_keys: List[str] = [k.strip() for k in settings.GROQ_API_KEY.split(",") if k.strip()]
        self.current_key_idx = 0
        self.client = self._init_client()
        self.model = self._get_model_name()

    def _init_client(self) -> Optional[OpenAI]:
        try:
            if self.provider == "groq":
                if not self.groq_keys:
                    logger.warning("GROQ_API_KEY não configurada no .env. Obtenha uma grátis em https://console.groq.com")
                active_key = self.groq_keys[self.current_key_idx] if self.groq_keys else "dummy_key"
                return OpenAI(
                    api_key=active_key,
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

    def _rotate_groq_key(self):
        """Alterna para a próxima chave Groq se houver mais de uma configurada."""
        if len(self.groq_keys) > 1:
            self.current_key_idx = (self.current_key_idx + 1) % len(self.groq_keys)
            new_key = self.groq_keys[self.current_key_idx]
            if self.client:
                self.client.api_key = new_key
            logger.info(f"[RateLimiter] 🔄 Rotacionando para chave Groq #{self.current_key_idx + 1}")

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
        Executa uma requisição de chat completion com proteção proativa contra Rate Limit.
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

        # Estima tokens para controle prévio de taxa
        estimated_tokens = rate_limiter.estimate_tokens(messages, tools)

        # Lista de modelos a tentar em ordem (com modelos de alta capacidade como fallback)
        candidate_models = [self.model]
        if self.provider == "groq":
            # groq/compound-mini possui limite de 70K TPM (quase 10x maior que os 8K do 120b)
            fallback_models = ["openai/gpt-oss-20b", "groq/compound-mini", "groq/compound"]
            for fm in fallback_models:
                if fm not in candidate_models:
                    candidate_models.append(fm)

        last_error = ""
        for current_model in candidate_models:
            # Checagem proativa: se a janela de tokens estiver quase esgotada, aguarda o reset antes de chamar
            if self.provider == "groq":
                rate_limiter.pre_flight_check(estimated_tokens, model_name=current_model)

            try:
                kwargs = {
                    "model": current_model,
                    "messages": messages,
                    "temperature": temperature,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                # Usa with_raw_response para capturar headers de rate limit na Groq
                if hasattr(self.client.chat.completions, "with_raw_response"):
                    raw_response = self.client.chat.completions.with_raw_response.create(**kwargs)
                    rate_limiter.update_from_headers(raw_response.headers)
                    response = raw_response.parse()
                else:
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
                is_rate_limit = "429" in last_error or "rate_limit" in last_error.lower() or "too many requests" in last_error.lower()

                if is_rate_limit:
                    wait_time = rate_limiter.handle_rate_limit_error(e)
                    logger.warning(
                        f"[RateLimiter] ⚠️ Limite de taxa (429) no modelo {current_model}. "
                        f"Aguardando {wait_time:.1f}s antes do próximo passo..."
                    )
                    # Se tiver mais de uma chave configurada, rotaciona imediatamente
                    if len(self.groq_keys) > 1:
                        self._rotate_groq_key()
                    else:
                        time.sleep(wait_time)
                else:
                    logger.warning(f"Erro com o modelo {current_model}: {last_error}. Tentando fallback...")

        return {
            "content": f"Erro na chamada do modelo ({self.provider}/{self.model}): {last_error}",
            "tool_calls": None
        }


llm_client = LLMClient()
