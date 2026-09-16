import os
from pathlib import Path
from typing import Optional
from src.config import settings


def write_file(filename: str, content: str) -> str:
    """
    Grava um arquivo no diretório de saída do workspace.
    """
    try:
        # Garante que caminhos fiquem dentro do workspace
        safe_path = settings.WORKSPACE_DIR / Path(filename).name
        safe_path.write_text(content, encoding="utf-8")
        return f"Arquivo '{safe_path.name}' salvo com sucesso ({len(content)} caracteres) em {safe_path}."
    except Exception as e:
        return f"Erro ao escrever arquivo '{filename}': {str(e)}"


def read_file(filename: str) -> str:
    """
    Lê o conteúdo de um arquivo do workspace.
    """
    try:
        safe_path = settings.WORKSPACE_DIR / Path(filename).name
        if not safe_path.exists():
            return f"Arquivo '{filename}' não encontrado no workspace."
        return safe_path.read_text(encoding="utf-8")
    except Exception as e:
        return f"Erro ao ler arquivo '{filename}': {str(e)}"


def list_workspace_files() -> str:
    """
    Lista todos os arquivos criados ou salvos no workspace.
    """
    try:
        files = list(settings.WORKSPACE_DIR.glob("*"))
        if not files:
            return "Nenhum arquivo no workspace no momento."
        
        output = ["Arquivos disponíveis no workspace:"]
        for f in files:
            if f.is_file():
                size_kb = round(f.stat().st_size / 1024, 2)
                output.append(f"- {f.name} ({size_kb} KB)")
        return "\n".join(output)
    except Exception as e:
        return f"Erro ao listar arquivos: {str(e)}"
