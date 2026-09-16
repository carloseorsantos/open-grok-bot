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

    def run(self, task: str, session_id: str = "default", max_steps: int = 6) -> str:
        """
        Executa o loop autônomo de raciocínio e ação (ReAct).
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": f"Tarefa a ser realizada: {task}"}
        ]

        step = 0
        final_response = ""

        while step < max_steps:
            step += 1
            response = llm_client.chat_completion(
                messages=messages,
                tools=self.tools_schema if self.tools_schema else None
            )

            content = response.get("content", "")
            tool_calls = response.get("tool_calls")

            # Se não houver chamadas de ferramenta, o bot concluiu a resposta
            if not tool_calls:
                final_response = content
                break

            # Constrói mensagem do assistente compatível com a Groq (sem campos como 'annotations')
            clean_assistant = {
                "role": "assistant",
                "content": content or None
            }
            if tool_calls:
                clean_assistant["tool_calls"] = [
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

            # Adiciona diretiva de consolidação para evitar loops infinitos de busca
            messages.append({
                "role": "user",
                "content": "Com base nas informações coletadas acima, formule a resposta final completa, clara e direta para o usuário."
            })

        if not final_response:
            final_response = "A tarefa atingiu o limite de passos antes de finalizar completamente."

        # Salvar histórico no banco
        memory_store.add_message(session_id=session_id, role="assistant", content=final_response, agent_name=self.name)
        return final_response
