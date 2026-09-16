from src.agents.base import Agent
from src.agents.specialists import (
    create_researcher_bot,
    create_web_navigator_bot,
    create_outbound_bot
)
from src.memory.db import memory_store


class ChiefOfStaff:
    """
    Agente Coordenador (Chief of Staff).
    Gerencia o time de bots, distribui subtarefas, coordena a memória compartilhada
    e garante que o projeto seja entregue finalizado.
    """
    def __init__(self):
        self.researcher = create_researcher_bot()
        self.web_navigator = create_web_navigator_bot()
        self.outbound = create_outbound_bot()

        self.tools = {
            "delegate_to_researcher": self._ask_researcher,
            "delegate_to_web_navigator": self._ask_web_navigator,
            "delegate_to_outbound": self._ask_outbound,
            "save_memory": self._save_memory,
            "get_memory": self._get_memory,
            "list_memories": self._list_memories,
        }

        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_researcher",
                    "description": "Delega uma tarefa de pesquisa factual na web ou busca de notícias ao Researcher Bot.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string", "description": "Descrição detalhada da pesquisa necessária"}
                        },
                        "required": ["task"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_web_navigator",
                    "description": "Delega uma tarefa de navegação em sites, cliques, formulários ou capturas de tela ao Web Navigator Bot.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string", "description": "Ações que o navegador deve executar"}
                        },
                        "required": ["task"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_outbound",
                    "description": "Delega uma tarefa de prospecção comercial, qualificação de leads ou redação de email/LinkedIn.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string", "description": "Instruções para o especialista de outbound"}
                        },
                        "required": ["task"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": "Salva uma informação importante na memória de longo prazo compartilhada entre todos os bots.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "Categoria (ex: 'cliente', 'regra', 'preferencia')"},
                            "key": {"type": "string", "description": "Chave identificadora"},
                            "value": {"type": "string", "description": "Conteúdo ou regra a ser lembrada"}
                        },
                        "required": ["category", "key", "value"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "get_memory",
                    "description": "Recupera uma informação da memória compartilhada.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "Categoria da memória"},
                            "key": {"type": "string", "description": "Chave"}
                        },
                        "required": ["category", "key"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_memories",
                    "description": "Lista as memórias e regras salvas anteriormente.",
                    "parameters": {"type": "object", "properties": {}}
                }
            }
        ]

        self.agent = Agent(
            name="Chief of Staff",
            role="Líder e Orquestrador de AI Teammates",
            system_prompt=(
                "Você é o Chief of Staff do Open Grok Bot. Você lidera uma equipe de AI Teammates que trabalham em paralelo. "
                "Seu estilo é direto, altamente competente, espirituoso e proativo (estilo Grok). "
                "Quando o usuário pede algo complexo:\n"
                "1. Analise o que é necessário.\n"
                "2. Delegue para os bots especialistas adequados (Researcher para buscas/notícias, Web Navigator para sites/telas, Outbound para prospecção).\n"
                "3. Use a memória compartilhada para lembrar preferências e fatos importantes.\n"
                "4. Entregue o resultado final pronto, claro e bem formatado."
            ),
            tools=self.tools,
            tools_schema=self.tools_schema
        )

    def _ask_researcher(self, task: str) -> str:
        return self.researcher.run(task)

    def _ask_web_navigator(self, task: str) -> str:
        return self.web_navigator.run(task)

    def _ask_outbound(self, task: str) -> str:
        return self.outbound.run(task)

    def _save_memory(self, category: str, key: str, value: str) -> str:
        memory_store.set_memory(category, key, value)
        return f"Memória salva em [{category}] '{key}': {value}"

    def _get_memory(self, category: str, key: str) -> str:
        res = memory_store.get_memory(category, key)
        if res is None:
            return f"Nenhuma memória encontrada para [{category}] '{key}'."
        return f"Memória recuperada: {res}"

    def _list_memories(self) -> str:
        mems = memory_store.list_memories()
        if not mems:
            return "Nenhuma memória registrada ainda."
        lines = ["Memórias salvas:"]
        for m in mems:
            lines.append(f"- [{m['category']}] {m['key']}: {m['value']}")
        return "\n".join(lines)

    def run(self, user_request: str, session_id: str = "default") -> str:
        return self.agent.run(user_request, session_id=session_id)


chief_of_staff = ChiefOfStaff()
