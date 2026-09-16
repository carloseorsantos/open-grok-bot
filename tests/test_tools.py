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
