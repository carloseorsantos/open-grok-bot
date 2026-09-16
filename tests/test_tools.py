from src.tools.filesystem import write_file, read_file, list_workspace_files


def test_filesystem_tools(tmp_path, monkeypatch):
    from src.config import settings
    monkeypatch.setattr(settings, "WORKSPACE_DIR", tmp_path)

    res_write = write_file("test.txt", "Conteúdo de teste para o bot.")
    assert "com sucesso" in res_write

    content = read_file("test.txt")
    assert content == "Conteúdo de teste para o bot."

    file_list = list_workspace_files()
    assert "test.txt" in file_list


def test_currency_tool(monkeypatch):
    from src.tools.finance import get_currency_quote

    # Test error handling / mock
    class MockResp:
        status_code = 200
        def json(self):
            return {
                "EURBRL": {
                    "name": "Euro/Real",
                    "bid": "5.90",
                    "ask": "5.91",
                    "high": "5.95",
                    "low": "5.88",
                    "pctChange": "0.1"
                }
            }

    import httpx
    monkeypatch.setattr(httpx, "get", lambda *args, **kwargs: MockResp())
    res = get_currency_quote("EUR-BRL")
    assert "Euro/Real" in res
    assert "R$ 5.90" in res
