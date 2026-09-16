try:
    from ddgs import DDGS
except ImportError:
    from duckduckgo_search import DDGS


def search_web(query: str, max_results: int = 3) -> str:
    """
    Pesquisa na web em tempo real usando DuckDuckGo (100% gratuito e sem chave de API).
    Retorna título, link e resumo dos principais resultados otimizados para economia de tokens.
    """
    try:
        results = []
        with DDGS() as ddgs:
            raw_results = ddgs.text(query, max_results=max_results)
            for r in raw_results:
                body = (r.get("body") or "").strip()
                if len(body) > 220:
                    body = body[:220] + "..."
                results.append({
                    "title": r.get("title"),
                    "url": r.get("href"),
                    "snippet": body
                })
        
        if not results:
            return f"Nenhum resultado encontrado para a busca: '{query}'."
        
        output = [f"Resultados para a busca '{query}':\n"]
        for idx, item in enumerate(results, 1):
            output.append(f"{idx}. {item['title']}\n   Link: {item['url']}\n   Resumo: {item['snippet']}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Erro ao realizar busca na web: {str(e)}"


def search_news(query: str, max_results: int = 3) -> str:
    """
    Pesquisa notícias recentes na web em tempo real usando DuckDuckGo (otimizado para tokens).
    """
    try:
        results = []
        with DDGS() as ddgs:
            raw_results = ddgs.news(query, max_results=max_results)
            for r in raw_results:
                body = (r.get("body") or "").strip()
                if len(body) > 220:
                    body = body[:220] + "..."
                results.append({
                    "title": r.get("title"),
                    "url": r.get("url"),
                    "date": r.get("date"),
                    "snippet": body
                })
        
        if not results:
            return f"Nenhuma notícia recente encontrada para: '{query}'."
        
        output = [f"Notícias recentes sobre '{query}':\n"]
        for idx, item in enumerate(results, 1):
            output.append(f"{idx}. [{item.get('date', 'Recente')}] {item['title']}\n   Link: {item['url']}\n   Resumo: {item['snippet']}\n")
        return "\n".join(output)
    except Exception as e:
        return f"Erro ao realizar busca de notícias: {str(e)}"
