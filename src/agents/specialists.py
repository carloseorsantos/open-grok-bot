from src.agents.base import Agent
from src.tools.search import search_web, search_news
from src.tools.filesystem import write_file, read_file, list_workspace_files
from src.tools.browser import browser_controller


def create_researcher_bot() -> Agent:
    tools = {
        "search_web": search_web,
        "search_news": search_news,
        "write_file": write_file,
        "read_file": read_file,
    }
    tools_schema = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Pesquisa na web em tempo real sobre qualquer tópico ou fato atual.",
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
                "name": "write_file",
                "description": "Salva um relatório ou documento no workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Nome do arquivo (ex: relatorio.md)"},
                        "content": {"type": "string", "description": "Conteúdo textual a ser gravado"}
                    },
                    "required": ["filename", "content"]
                }
            }
        }
    ]
    return Agent(
        name="Researcher",
        role="Pesquisador e Analista de Mercado",
        system_prompt=(
            "Você é o Researcher Bot, o especialista em pesquisa rápida, precisa e factual do time Open Grok Bot. "
            "Seu trabalho é buscar informações recentes na web em tempo real, filtrar ruídos, sintetizar dados e compilar relatórios claros.\n"
            "REGRA DE FORMATAÇÃO: NUNCA crie tabelas com barras (| ... |). Sempre estruture os dados em tópicos com marcadores (•), negrito e emojis, para leitura agradável no celular."
        ),
        tools=tools,
        tools_schema=tools_schema
    )


def create_web_navigator_bot() -> Agent:
    tools = {
        "browser_navigate": browser_controller.navigate,
        "browser_get_content": browser_controller.get_content,
        "browser_click": browser_controller.click,
        "browser_type": browser_controller.type_text,
        "browser_screenshot": browser_controller.take_screenshot,
    }
    tools_schema = [
        {
            "type": "function",
            "function": {
                "name": "browser_navigate",
                "description": "Abre o navegador e acessa uma URL específica.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {"type": "string", "description": "URL completa para navegar"}
                    },
                    "required": ["url"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_get_content",
                "description": "Lê o texto, links e botões da página aberta atualmente no navegador.",
                "parameters": {"type": "object", "properties": {}}
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_click",
                "description": "Clica em um elemento da página (pelo texto ou seletor CSS).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector_or_text": {"type": "string", "description": "Texto do botão/link ou seletor CSS"}
                    },
                    "required": ["selector_or_text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_type",
                "description": "Digita texto em um campo de entrada da página.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "selector": {"type": "string", "description": "Seletor do campo de texto"},
                        "text": {"type": "string", "description": "Texto para digitar"}
                    },
                    "required": ["selector", "text"]
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "browser_screenshot",
                "description": "Tira uma captura de tela da página atual para auditoria ou visualização.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Nome do arquivo (ex: print.png)"}
                    }
                }
            }
        }
    ]
    return Agent(
        name="Web Navigator",
        role="Especialista em Automação Web e Computer Use",
        system_prompt=(
            "Você é o Web Navigator Bot do time Open Grok Bot. Você tem o controle de um navegador real na máquina. "
            "Você navega em sites, clica em botões, preenche dados e tira prints para comprovar o resultado."
        ),
        tools=tools,
        tools_schema=tools_schema
    )


def create_outbound_bot() -> Agent:
    tools = {
        "search_web": search_web,
        "write_file": write_file,
    }
    tools_schema = [
        {
            "type": "function",
            "function": {
                "name": "search_web",
                "description": "Pesquisa perfis de empresas e potenciais clientes.",
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
                "name": "write_file",
                "description": "Salva rascunhos de mensagens ou listas de leads no workspace.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "filename": {"type": "string", "description": "Nome do arquivo"},
                        "content": {"type": "string", "description": "Conteúdo"}
                    },
                    "required": ["filename", "content"]
                }
            }
        }
    ]
    return Agent(
        name="Sales Outbound",
        role="Especialista em Prospecção e Mensagens",
        system_prompt=(
            "Você é o Sales Outbound Bot do time Open Grok Bot. Seu foco é pesquisar empresas, qualificar leads "
            "e redigir abordagens persuasivas e personalizadas para email ou LinkedIn."
        ),
        tools=tools,
        tools_schema=tools_schema
    )
