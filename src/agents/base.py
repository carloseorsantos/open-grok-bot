import json
import logging
from typing import Any, Callable, Dict, List, Optional
from src.llm.client import llm_client
from src.memory.db import memory_store

logger = logging.getLogger("OpenGrokBot.Agent")


class Agent:
    """
    Classe base para um AI Teammate (Grok Bot).
    Gerencia o loop de execução autônomo, chamada de ferramentas e histórico.
    """
    def __init__(
        self,
        name: str,
        role: str,
        system_prompt: str,
        tools: Optional[Dict[str, Callable]] = None,
        tools_schema: Optional[List[dict]] = None
    ):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tools = tools or {}
        self.tools_schema = tools_schema or []

    def execute_tool(self, tool_name: str, arguments: dict) -> str:
        """Executa uma ferramenta registrada com tratamento de erro."""
        if tool_name not in self.tools:
            return f"Ferramenta '{tool_name}' não encontrada ou não permitida para o agente {self.name}."
        try:
            func = self.tools[tool_name]
            result = func(**arguments)
            return str(result)
        except Exception as e:
            return f"Erro ao executar ferramenta '{tool_name}': {str(e)}"

    def run(self, task: str, session_id: str = "default", max_steps: int = 2) -> str:
        """
        Executa o loop autônomo de raciocínio e ação com garantia de conclusão rápida.
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Tarefa a ser realizada: {task}"}
        ]

        step = 0
        final_response = ""

        while step < max_steps:
            step += 1
            # Na última iteração do loop, não passamos tools para forçar o modelo a sintetizar a resposta
            allow_tools = (step < max_steps) and bool(self.tools_schema)

            response = llm_client.chat_completion(
                messages=messages,
                tools=self.tools_schema if allow_tools else None
            )

            content = response.get("content", "")
            tool_calls = response.get("tool_calls")

            # Se não houver chamadas de ferramenta, o bot concluiu a resposta
            if not tool_calls:
                final_response = content
                break

            # Constrói mensagem do assistente compatível com a Groq
            clean_assistant = {
                "role": "assistant",
                "content": content or None,
                "tool_calls": [
                    {
                        "id": tc["id"],
                        "type": "function",
                        "function": {
                            "name": tc["name"],
                            "arguments": json.dumps(tc["arguments"]) if isinstance(tc["arguments"], dict) else str(tc["arguments"])
                        }
                    }
                    for tc in tool_calls
                ]
            }
            messages.append(clean_assistant)

            # Executa as ferramentas e envia as respostas com role="tool"
            for tc in tool_calls:
                t_name = tc["name"]
                t_args = tc["arguments"]
                logger.info(f"[{self.name}] Executando ferramenta: {t_name} com args: {t_args}")
                
                tool_output = self.execute_tool(t_name, t_args)
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],
                    "content": str(tool_output)
                })

            # Adiciona diretiva para consolidar a resposta sem loops
            messages.append({
                "role": "user",
                "content": (
                    "Com base nas informações coletadas acima pelas ferramentas, elabore a resposta final completa, clara e direta para o usuário agora.\n"
                    "REGRA DE FORMATAÇÃO: NUNCA use tabelas com barras (|). "
                    "Formate a resposta em tópicos, cartões e bullet points (•) usando negrito e emojis, perfeitamente legível no celular."
                )
            })

        if not final_response:
            # Fallback garantido: força geração direta de texto sem tools
            fallback_resp = llm_client.chat_completion(messages=messages, tools=None)
            final_response = fallback_resp.get("content") or "Aqui estão as informações obtidas pelas ferramentas."

        # Salvar histórico no banco
        memory_store.add_message(session_id=session_id, role="assistant", content=final_response, agent_name=self.name)
        return final_response
