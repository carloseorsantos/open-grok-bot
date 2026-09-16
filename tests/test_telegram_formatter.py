from src.interfaces.telegram_bot import convert_tables_to_cards, format_for_telegram


def test_convert_tables_to_cards():
    table_markdown = (
        "Aqui está o comparativo:\n\n"
        "| Moeda | Cotação | Variação |\n"
        "|---|---|---|\n"
        "| USD | R$ 5,75 | +0.2% |\n"
        "| EUR | R$ 6,10 | -0.1% |\n\n"
        "Fim do resumo."
    )
    result = convert_tables_to_cards(table_markdown)
    assert "|" not in result
    assert "• <b>Moeda:</b> USD" in result
    assert "• <b>Cotação:</b> R$ 5,75" in result
    assert "• <b>Moeda:</b> EUR" in result
    assert "Fim do resumo." in result


def test_format_for_telegram_formatting():
    raw = (
        "**Importante**: Veja o link [Google](https://google.com) e leia a citação:\n"
        "> Esta é uma citação inspiradora\n"
        "Use o comando `python main.py` para rodar."
    )
    formatted = format_for_telegram(raw)
    assert "<b>Importante</b>" in formatted
    assert '<a href="https://google.com">Google</a>' in formatted
    assert "<blockquote>Esta é uma citação inspiradora</blockquote>" in formatted
    assert "<code>python main.py</code>" in formatted


def test_format_for_telegram_code_blocks():
    raw = (
        "Aqui está o script:\n"
        "```python\n"
        "def hello():\n"
        "    return 'world'\n"
        "```"
    )
    formatted = format_for_telegram(raw)
    assert "<pre>" in formatted
    assert "def hello():" in formatted
    assert "</pre>" in formatted
