import json
import logging
import re
import time
from typing import Any, Dict, List, Optional

logger = logging.getLogger("OpenGrokBot.RateLimiter")


def parse_groq_duration(duration_str: Optional[str]) -> float:
    """
    Converte strings de duração da Groq em segundos float.
    Exemplos: '3.435s' -> 3.435, '2m59.56s' -> 179.56, '750ms' -> 0.75
    """
    if not duration_str:
        return 0.0

    duration_str = str(duration_str).strip().lower()

    # Caso em milissegundos
    ms_match = re.search(r"([\d.]+)ms", duration_str)
    if ms_match:
        return float(ms_match.group(1)) / 1000.0

    # Caso com minutos e segundos: 2m59.56s
    m_match = re.search(r"(\d+)m", duration_str)
    s_match = re.search(r"([\d.]+)s", duration_str)

    total_seconds = 0.0
    if m_match:
        total_seconds += float(m_match.group(1)) * 60.0
    if s_match:
        total_seconds += float(s_match.group(1))
    elif not m_match:
        try:
            total_seconds = float(duration_str)
        except ValueError:
            total_seconds = 0.0

    return max(0.0, total_seconds)


class GroqRateLimiter:
    """
    Gerenciador proativo de limites de taxa (Rate Limits) para a API da Groq.
    Monitora TPM (Tokens Por Minuto) e RPM em tempo real usando os headers HTTP da Groq,
    evitando erros 429 antes mesmo da requisição ser disparada.
    """
    def __init__(self, default_min_tokens: int = 1500):
        self.default_min_tokens = default_min_tokens

        # Estado atual de tokens
        self.remaining_tokens: Optional[int] = None
        self.limit_tokens: Optional[int] = None
        self.tokens_reset_at: float = 0.0

        # Estado atual de requisições
        self.remaining_requests: Optional[int] = None
        self.requests_reset_at: float = 0.0

    def estimate_tokens(self, messages: List[Dict[str, Any]], tools: Optional[List[Dict[str, Any]]] = None) -> int:
        """
        Estima a quantidade de tokens necessários para uma chamada.
        Aproximação: 1 token ~= 3.5 a 4 caracteres em português/código + folga para saída.
        """
        total_chars = 0
        for m in messages:
            content = m.get("content")
            if content:
                total_chars += len(str(content))
            tool_calls = m.get("tool_calls")
            if tool_calls:
                total_chars += len(str(tool_calls))

        if tools:
            total_chars += len(json.dumps(tools))

        # Estima tokens de entrada + 600 tokens reservados para resposta do modelo
        estimated_input = int(total_chars / 3.6)
        estimated_total = estimated_input + 600
        return max(100, estimated_total)

    def pre_flight_check(self, estimated_tokens: int, model_name: str = ""):
        """
        Verificação proativa antes de enviar a requisição:
        Se soubermos que os tokens restantes não cobrem a requisição atual,
        aguarda o tempo de reset da janela (geralmente poucos segundos) em vez de tomar 429.
        """
        now = time.time()

        # Se o reset já passou, nosso saldo de tokens foi renovado na Groq
        if now >= self.tokens_reset_at:
            return

        # Se sabemos que os tokens restantes são insuficientes
        if self.remaining_tokens is not None and self.remaining_tokens < estimated_tokens:
            wait_seconds = max(0.1, self.tokens_reset_at - now) + 0.2
            logger.warning(
                f"[RateLimiter] ⏳ Cota de tokens baixa ({self.remaining_tokens} restantes, ~{estimated_tokens} necessários). "
                f"Aguardando {wait_seconds:.2f}s para renovação da janela na Groq..."
            )
            time.sleep(min(wait_seconds, 15.0))

    def update_from_headers(self, headers: Any):
        """
        Atualiza o estado interno a partir dos headers HTTP reais retornados pela Groq.
        """
        if not headers:
            return

        now = time.time()

        # Extrai remaining tokens
        rem_tok = headers.get("x-ratelimit-remaining-tokens")
        if rem_tok is not None:
            try:
                self.remaining_tokens = int(rem_tok)
            except Exception:
                pass

        # Extrai reset tokens
        reset_tok = headers.get("x-ratelimit-reset-tokens")
        if reset_tok:
            duration = parse_groq_duration(reset_tok)
            self.tokens_reset_at = now + duration

        # Extrai limit tokens
        lim_tok = headers.get("x-ratelimit-limit-tokens")
        if lim_tok is not None:
            try:
                self.limit_tokens = int(lim_tok)
            except Exception:
                pass

        # Extrai remaining requests
        rem_req = headers.get("x-ratelimit-remaining-requests")
        if rem_req is not None:
            try:
                self.remaining_requests = int(rem_req)
            except Exception:
                pass

        logger.debug(
            f"[RateLimiter] Headers: remaining_tokens={self.remaining_tokens}/{self.limit_tokens}, "
            f"reset_in={max(0.0, self.tokens_reset_at - now):.2f}s, remaining_requests={self.remaining_requests}"
        )

    def handle_rate_limit_error(self, error: Exception) -> float:
        """
        Calcula o tempo de espera necessário caso ocorra uma resposta 429 da API.
        Lê retry-after dos headers do erro se disponível.
        """
        wait_time = 4.0 # fallback seguro padrão

        response = getattr(error, "response", None)
        if response and hasattr(response, "headers"):
            headers = response.headers
            self.update_from_headers(headers)

            retry_after = headers.get("retry-after")
            if retry_after:
                wait_time = parse_groq_duration(retry_after)
            elif headers.get("x-ratelimit-reset-tokens"):
                wait_time = parse_groq_duration(headers.get("x-ratelimit-reset-tokens"))

        return max(1.5, wait_time + 0.5)


rate_limiter = GroqRateLimiter()
