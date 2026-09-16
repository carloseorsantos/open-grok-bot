import re
from pathlib import Path
from typing import Optional
from playwright.sync_api import sync_playwright, Browser, Page, Playwright
from src.config import settings


class BrowserController:
    """
    Controlador do navegador para o Open Grok Bot.
    Permite aos agentes navegar, interagir com formulários, extrair texto e tirar prints.
    """
    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._page: Optional[Page] = None

    def _ensure_browser(self):
        if not self._playwright:
            self._playwright = sync_playwright().start()
        if not self._browser:
            self._browser = self._playwright.chromium.launch(
                headless=settings.BROWSER_HEADLESS,
                args=["--disable-dev-shm-usage", "--no-sandbox"]
            )
        if not self._page:
            context = self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            )
            self._page = context.new_page()
            self._page.set_default_timeout(settings.BROWSER_TIMEOUT)

    def navigate(self, url: str) -> str:
        """Navega para uma URL e retorna o título e resumo da página."""
        try:
            self._ensure_browser()
            if not url.startswith("http://") and not url.startswith("https://"):
                url = "https://" + url
            self._page.goto(url, wait_until="domcontentloaded")
            title = self._page.title()
            return f"Navegado com sucesso para: {url}\nTítulo da página: '{title}'"
        except Exception as e:
            return f"Erro ao navegar para {url}: {str(e)}"

    def get_content(self, max_length: int = 2000) -> str:
        """Extrai o texto legível e os elementos clicáveis principais da página atual (otimizado para tokens)."""
        try:
            self._ensure_browser()
            if not self._page or not self._page.url:
                return "Nenhuma página aberta no navegador no momento."
            
            # Extrair texto limpo
            text = self._page.inner_text("body")
            clean_text = re.sub(r"\n\s*\n", "\n\n", text).strip()
            
            # Extrair links e botões clicáveis principais
            elements = self._page.query_selector_all("a, button, input[type='submit']")
            interactive = []
            for el in elements[:12]:
                try:
                    el_text = el.inner_text().strip()
                    if el_text:
                        interactive.append(f"[{el.evaluate('e => e.tagName.toLowerCase()')}] '{el_text}'")
                except Exception:
                    pass

            summary = f"URL Atual: {self._page.url}\nTítulo: {self._page.title()}\n\n"
            if interactive:
                summary += "Elementos interativos:\n" + "\n".join(interactive[:8]) + "\n\n"
            summary += "Conteúdo da página:\n" + clean_text[:max_length]
            return summary
        except Exception as e:
            return f"Erro ao extrair conteúdo da página: {str(e)}"

    def click(self, selector_or_text: str) -> str:
        """Clica em um elemento por seletor CSS ou texto visível."""
        try:
            self._ensure_browser()
            # Tenta clicar pelo texto se não parecer seletor CSS
            if " " in selector_or_text and not any(c in selector_or_text for c in [">", "#", ".", "["]):
                self._page.get_by_text(selector_or_text).first.click()
            else:
                try:
                    self._page.click(selector_or_text, timeout=5000)
                except Exception:
                    self._page.get_by_text(selector_or_text).first.click()
            return f"Elemento '{selector_or_text}' clicado com sucesso."
        except Exception as e:
            return f"Erro ao clicar em '{selector_or_text}': {str(e)}"

    def type_text(self, selector: str, text: str) -> str:
        """Digita texto em um campo de formulário."""
        try:
            self._ensure_browser()
            self._page.fill(selector, text)
            return f"Texto inserido com sucesso no campo '{selector}'."
        except Exception as e:
            return f"Erro ao digitar no campo '{selector}': {str(e)}"

    def take_screenshot(self, name: str = "screenshot.png") -> str:
        """Tira uma captura de tela da página atual e salva no diretório de screenshots."""
        try:
            self._ensure_browser()
            path = settings.SCREENSHOTS_DIR / name
            self._page.screenshot(path=str(path), full_page=False)
            return f"Captura de tela salva com sucesso em: {path}"
        except Exception as e:
            return f"Erro ao tirar captura de tela: {str(e)}"

    def close(self):
        """Fecha o navegador."""
        if self._browser:
            self._browser.close()
            self._browser = None
        if self._playwright:
            self._playwright.stop()
            self._playwright = None
        self._page = None


browser_controller = BrowserController()
