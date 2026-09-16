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


def test_code_runner_tool(tmp_path, monkeypatch):
    from src.config import settings
    from src.tools.code_runner import run_python_code
    monkeypatch.setattr(settings, "WORKSPACE_DIR", tmp_path)

    # Test math calculation
    output = run_python_code("print(10 * 5 + 7)")
    assert "57" in output

    # Test syntax error handling
    output_err = run_python_code("print(invalid syntax")
    assert "SyntaxError" in output_err or "Erros/Avisos" in output_err

    # Test empty code
    assert "vazio" in run_python_code("")


def test_image_generator_mock(tmp_path, monkeypatch):
    from src.config import settings
    from src.tools.image import generate_image
    monkeypatch.setattr(settings, "WORKSPACE_DIR", tmp_path)

    class MockHttpxClient:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            pass
        def get(self, url):
            class MockResp:
                status_code = 200
                content = b"\xff\xd8\xff\xe0FAKEJPEGDATA"
            return MockResp()

    import httpx
    monkeypatch.setattr(httpx, "Client", MockHttpxClient)

    res = generate_image("a futuristic space station")
    assert "sucesso" in res
    assert (tmp_path / "flux_a_futuristic_space_stati").name or any(f.name.startswith("flux_") for f in tmp_path.glob("*.jpg"))

