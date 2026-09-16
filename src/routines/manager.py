from typing import Any, Dict, List, Optional
from src.memory.db import memory_store
from src.agents.orchestrator import chief_of_staff


class RoutineManager:
    """
    Gerenciador de Rotinas automatizadas ("Show a Bot how it's done").
    Permite criar, salvar, listar e executar rotinas repetíveis pelos bots.
    """
    def __init__(self):
        self._ensure_default_routines()

    def _ensure_default_routines(self):
        defaults = [
            {
                "name": "daily-tech-digest",
                "description": "Pesquisa as principais notícias de tecnologia e IA de hoje e gera um resumo executivo.",
                "prompt_template": "Pesquise as notícias mais relevantes de hoje sobre tecnologia e inteligência artificial. Resuma os 3 pontos mais impactantes e salve um relatório em tech_digest.md."
            },
            {
                "name": "company-recon",
                "description": "Investiga uma empresa, seus produtos e gera um rascunho de abordagem para parcerias.",
                "prompt_template": "Pesquise sobre a empresa {company}. Descubra o que fazem, quem são seus clientes e crie uma abordagem personalizada de apresentação."
            },
            {
                "name": "web-health-check",
                "description": "Acessa uma página web, tira um print e analisa se o site está online e com layout íntegro.",
                "prompt_template": "Acesse a URL {url} com o navegador, capture uma screenshot e verifique se o site está carregando corretamente e quais elementos estão visíveis."
            }
        ]
        for d in defaults:
            if not memory_store.get_routine(d["name"]):
                memory_store.save_routine(d["name"], d["description"], d["prompt_template"])

    def create_routine(self, name: str, description: str, prompt_template: str, schedule: Optional[str] = None):
        """Salva uma nova rotina no banco de dados."""
        memory_store.save_routine(name, description, prompt_template, schedule)
        return f"Rotina '{name}' salva com sucesso!"

    def delete_routine(self, name: str) -> str:
        """Remove uma rotina do banco de dados."""
        success = memory_store.delete_routine(name)
        if success:
            return f"Rotina '{name}' removida com sucesso!"
        return f"Rotina '{name}' não encontrada."

    def list_routines(self) -> List[Dict[str, Any]]:
        """Retorna todas as rotinas salvas."""
        return memory_store.list_routines()

    def run_routine(self, name: str, params: Optional[Dict[str, str]] = None) -> str:
        """
        Executa uma rotina salva substituindo as variáveis fornecidas.
        """
        routine = memory_store.get_routine(name)
        if not routine:
            return f"Rotina '{name}' não encontrada. Use list_routines() para ver as disponíveis."

        template = routine["prompt_template"]
        if params:
            for k, v in params.items():
                template = template.replace(f"{{{k}}}", v)

        # Envia para o Chief of Staff orquestrar
        return chief_of_staff.run(f"[Executando Rotina: {name}]\n{template}")


routine_manager = RoutineManager()
