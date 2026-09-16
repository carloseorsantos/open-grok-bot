import re
import time
import urllib.parse
from pathlib import Path
from typing import Optional
import httpx
from src.config import settings


def generate_image(prompt: str, filename: Optional[str] = None) -> str:
    """
    Gera uma imagem de alta qualidade usando o modelo Flux.1 (mesmo modelo do Grok) via Pollinations.ai (100% gratuito).
    Salva a imagem no workspace e retorna o caminho do arquivo gerado.
    """
    try:
        if not prompt or not prompt.strip():
            return "Erro: Prompt de imagem não pode estar vazio."

        safe_name = filename
        if not safe_name:
            # Cria nome limpo baseado no prompt e timestamp
            slug = re.sub(r"[^a-zA-Z0-9]+", "_", prompt.strip()[:25]).strip("_").lower()
            safe_name = f"flux_{slug}_{int(time.time())}.jpg"
        elif not safe_name.endswith((".jpg", ".png", ".jpeg")):
            safe_name = f"{safe_name}.jpg"

        output_path = settings.WORKSPACE_DIR / safe_name
        encoded_prompt = urllib.parse.quote(prompt.strip())
        
        # Endpoint Flux.1 de alta velocidade
        url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&width=1024&height=1024&nologo=true&seed={int(time.time() * 1000) % 999999}"

        with httpx.Client(timeout=45.0) as client:
            resp = client.get(url)
            if resp.status_code != 200:
                return f"Falha ao gerar imagem (Status {resp.status_code}). Tente novamente com outro prompt."
            
            output_path.write_bytes(resp.content)

        return f"🎨 Imagem gerada com sucesso com Flux.1!\nArquivo: {output_path.name}\nCaminho: {output_path}"
    except Exception as e:
        return f"Erro ao gerar imagem: {str(e)}"
