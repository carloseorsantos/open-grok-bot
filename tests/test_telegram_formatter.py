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

def test_format_headings_and_rules():
    raw = (
        "# Título Principal\n"
        "### Subtítulo Três\n"
        "---\n"
        "Conteúdo normal."
    )
    formatted = format_for_telegram(raw)
    assert "<b>📌 Título Principal</b>" in formatted
    assert "<b>▪️ Subtítulo Três</b>" in formatted
    assert "— — —" in formatted
    assert "Conteúdo normal." in formatted


def test_balance_html_tags():
    from src.interfaces.telegram_bot import balance_html_tags
    broken_html = "<b>Texto em negrito com <i>itálico sem fechar"
    balanced = balance_html_tags(broken_html)
    assert balanced.endswith("</i></b>") or balanced.endswith("</b></i>")


def test_clean_text_fallback():
    from src.interfaces.telegram_bot import clean_text_fallback
    raw = "### Título\nVeja **este texto** e [link](https://exemplo.com)"
    cleaned = clean_text_fallback(raw)
    assert "###" not in cleaned
    assert "**" not in cleaned
    assert "📌 Título" in cleaned
    assert "este texto" in cleaned
    assert "link (https://exemplo.com)" in cleaned
