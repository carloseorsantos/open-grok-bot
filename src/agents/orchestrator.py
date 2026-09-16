from src.agents.base import Agent
from src.agents.specialists import (
    create_researcher_bot,
    create_web_navigator_bot,
    create_outbound_bot,
    create_code_analyst_bot
)
from src.tools.finance import get_currency_quote
from src.tools.search import search_web, search_news
from src.tools.browser import browser_controller
from src.tools.filesystem import write_file, read_file
from src.tools.image import generate_image
from src.tools.code_runner import run_python_code
from src.memory.db import memory_store


class ChiefOfStaff:
    """
    Agente Coordenador (Chief of Staff).
    Lidera a equipe de AI Teammates, responde de forma rápida e proativa,
    utiliza ferramentas diretamente para respostas ágeis e delega projetos complexos.
    """
    def __init__(self):
        self.researcher = create_researcher_bot()
        self.web_navigator = create_web_navigator_bot()
        self.outbound = create_outbound_bot()
        self.code_analyst = create_code_analyst_bot()

        self.tools = {
            "get_currency_quote": get_currency_quote,
            "search_web": search_web,
            "search_news": search_news,
            "generate_image": generate_image,
            "run_python_code": run_python_code,
            "browser_navigate": browser_controller.navigate,
            "browser_screenshot": browser_controller.take_screenshot,
            "save_memory": self._save_memory,
            "get_memory": self._get_memory,
            "list_memories": self._list_memories,
            "create_routine": self._create_routine,
            "delete_routine": self._delete_routine,
            "list_routines": self._list_routines,
            "delegate_to_outbound": self._ask_outbound,
            "delegate_to_code_analyst": self._ask_code_analyst,
        }

        self.tools_schema = [
            {
                "type": "function",
                "function": {
                    "name": "get_currency_quote",
                    "description": "Obtém cotações atualizadas em tempo real de moedas e criptos (EUR-BRL, USD-BRL, BTC-BRL).",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "currency_pair": {"type": "string", "description": "Par de moedas (ex: 'EUR-BRL', 'USD-BRL')"}
                        },
                        "required": ["currency_pair"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_web",
                    "description": "Pesquisa na web em tempo real sobre qualquer assunto, fatos ou informações recentes.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Termo de busca"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "search_news",
                    "description": "Pesquisa notícias recentes na web.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "query": {"type": "string", "description": "Assunto da notícia"}
                        },
                        "required": ["query"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_navigate",
                    "description": "Abre o navegador e acessa uma URL.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "url": {"type": "string", "description": "URL para navegar"}
                        },
                        "required": ["url"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "browser_screenshot",
                    "description": "Tira uma captura de tela da página atual no navegador.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Nome do arquivo (ex: print.png)"}
                        }
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "save_memory",
                    "description": "Salva uma informação importante na memória compartilhada.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "category": {"type": "string", "description": "Categoria"},
                            "key": {"type": "string", "description": "Chave"},
                            "value": {"type": "string", "description": "Valor"}
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
                            "category": {"type": "string", "description": "Categoria"},
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
                    "description": "Lista as principais memórias e regras compartilhadas entre os bots.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_outbound",
                    "description": "Delega uma tarefa complexa de prospecção comercial ou copywriting ao Outbound Bot.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string", "description": "Descrição da tarefa de outbound"}
                        },
                        "required": ["task"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "generate_image",
                    "description": "Gera uma imagem de alta fidelidade usando o modelo Flux.1 (o mesmo do Grok) a partir de um prompt.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "prompt": {"type": "string", "description": "Prompt detalhado da imagem em inglês ou português"},
                            "filename": {"type": "string", "description": "Nome opcional do arquivo (ex: arte.jpg)"}
                        },
                        "required": ["prompt"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "run_python_code",
                    "description": "Executa código Python no ambiente para cálculos matemáticos, processamento de dados ou automação.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "code": {"type": "string", "description": "Código Python válido"}
                        },
                        "required": ["code"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "create_routine",
                    "description": "Cria e salva uma rotina de automação personalizada ('Show a Bot how it's done').",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Identificador único da rotina (ex: bitcoin-monitor)"},
                            "description": {"type": "string", "description": "Breve descrição do que a rotina faz"},
                            "prompt_template": {"type": "string", "description": "Instruções completas da tarefa com placeholders {var} se houver"}
                        },
                        "required": ["name", "description", "prompt_template"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delete_routine",
                    "description": "Remove uma rotina salva pelo nome.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Nome da rotina a remover"}
                        },
                        "required": ["name"]
                    }
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "list_routines",
                    "description": "Lista todas as rotinas de automação disponíveis.",
                    "parameters": {"type": "object", "properties": {}}
                }
            },
            {
                "type": "function",
                "function": {
                    "name": "delegate_to_code_analyst",
                    "description": "Delega uma tarefa complexa de análise de dados, scripts ou programação ao Code Analyst Bot.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "task": {"type": "string", "description": "Descrição detalhada da tarefa"}
                        },
                        "required": ["task"]
                    }
                }
            }
        ]

        self.agent = Agent(
            name="Chief of Staff",
            role="Líder e Orquestrador de AI Teammates",
            system_prompt=(
                "Você é o Chief of Staff do Open Grok Bot. Você lidera uma equipe de AI Teammates de alta performance. "
                "Seu estilo é ágil, direto, espirituoso e altamente competente (estilo Grok).\n\n"
                "COMO VOCÊ TRABALHA:\n"
                "1. Seja ultrarrápido: se o usuário perguntar cotações, use get_currency_quote imediatamente.\n"
                "2. Se o usuário pedir para criar ou gerar imagem, use generate_image.\n"
                "3. Se o usuário pedir cálculos matemáticos, análise de dados ou código Python, use run_python_code.\n"
                "4. Se o usuário pedir para criar uma rotina ('ensinar o bot' / 'show a bot how it's done'), use create_routine.\n"
                "5. Se o usuário perguntar fatos ou notícias recentes, use search_web ou search_news.\n"
                "6. Responda diretamente ao usuário assim que receber os dados da ferramenta. Não faça buscas repetidas.\n\n"
                "REGRAS DE FORMATAÇÃO VISUAL (OBRIGATÓRIO PARA TELAS DE CELULAR/TELEGRAM):\n"
                "- NUNCA, SOB NENHUMA HIPÓTESE, CRIE TABELAS COM BARRAS (| ... | ... |). Em celulares e no Telegram, tabelas quebram e ficam ilegíveis!\n"
                "- Sempre formate dados, comparações, listas e preços em CARTÕES ou TÓPICOS usando negrito, bullet points (•) e quebras de linha limpas.\n"
                "- Use emojis temáticos como marcadores visuais (ex: 📍 para locais, 💰 para preços/aluguel, 📈 para alta, 📉 para baixa, ✅ para prós, ⚠️ para contras).\n"
                "- Mantenha a leitura visualmente limpa, leve e moderna."
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

    def _ask_code_analyst(self, task: str) -> str:
        return self.code_analyst.run(task)

    def _create_routine(self, name: str, description: str, prompt_template: str) -> str:
        memory_store.save_routine(name, description, prompt_template)
        return f"Rotina '{name}' criada e salva com sucesso!"

    def _delete_routine(self, name: str) -> str:
        success = memory_store.delete_routine(name)
        if success:
            return f"Rotina '{name}' removida com sucesso!"
        return f"Rotina '{name}' não encontrada."

    def _list_routines(self) -> str:
        routines = memory_store.list_routines()
        if not routines:
            return "Nenhuma rotina cadastrada no momento."
        lines = ["Rotinas salvas:"]
        for r in routines:
            lines.append(f"• {r['name']}: {r['description']}")
        return "\n".join(lines)

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
