import httpx
from typing import Optional


def get_currency_quote(currency_pair: str = "EUR-BRL") -> str:
    """
    Obtém cotações em tempo real de moedas (ex: EUR-BRL, USD-BRL, BTC-BRL).
    Retorna valor de compra, venda, máxima, mínima e variação do dia.
    """
    try:
        pair = currency_pair.upper().replace("/", "-").strip()
        if "-" not in pair:
            pair = f"{pair}-BRL"

        url = f"https://economia.awesomeapi.com.br/last/{pair}"
        resp = httpx.get(url, timeout=10.0)
        
        if resp.status_code != 200:
            return f"Não foi possível obter a cotação para '{currency_pair}'."

        data = resp.json()
        key = pair.replace("-", "")
        item = data.get(key)
        if not item:
            # Pega o primeiro item disponível
            item = next(iter(data.values()), None)

        if not item:
            return f"Dados de cotação não encontrados para '{currency_pair}'."

        name = item.get("name", pair)
        bid = item.get("bid")
        ask = item.get("ask")
        high = item.get("high")
        low = item.get("low")
        pct = item.get("pctChange")

        return (
            f"Cotação em tempo real de {name}:\n"
            f"• Compra: R$ {bid}\n"
            f"• Venda: R$ {ask}\n"
            f"• Máxima do dia: R$ {high}\n"
            f"• Mínima do dia: R$ {low}\n"
            f"• Variação: {pct}%\n"
        )
    except Exception as e:
        return f"Erro ao consultar cotação: {str(e)}"
