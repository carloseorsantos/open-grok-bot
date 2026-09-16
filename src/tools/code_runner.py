import ast
import os
import sys
import subprocess
from pathlib import Path
from src.config import settings


def auto_print_last_expr(code: str) -> str:
    """Se a última instrução for uma expressão (sem print), envolve-a em print()."""
    try:
        tree = ast.parse(code)
        if tree.body and isinstance(tree.body[-1], ast.Expr):
            # Não altera se a expressão já for uma chamada de print
            last_expr = tree.body[-1]
            if isinstance(last_expr.value, ast.Call) and getattr(last_expr.value.func, "id", None) == "print":
                return code
            tree.body[-1] = ast.Expr(value=ast.Call(
                func=ast.Name(id="print", ctx=ast.Load()),
                args=[last_expr.value],
                keywords=[]
            ))
            ast.fix_missing_locations(tree)
            return ast.unparse(tree)
    except Exception:
        pass
    return code


def run_python_code(code: str, timeout: int = 15) -> str:
    """
    Executa um script Python no diretório do workspace.
    Permite realizar cálculos matemáticos avançados, processar arquivos de dados (CSV, JSON),
    ou gerar análises e gráficos com visualização.
    """
    if not code or not code.strip():
        return "Erro: O código fornecido está vazio."

    # Remove blocos markdown caso o LLM tenha enviado ```python ... ```
    clean_code = code.strip()
    if clean_code.startswith("```"):
        lines = clean_code.split("\n")
        if lines[0].startswith("```"):
            lines = lines[1:]
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_code = "\n".join(lines).strip()

    clean_code = auto_print_last_expr(clean_code)

    # Cria script temporário dentro do workspace
    temp_script = settings.WORKSPACE_DIR / f"_temp_runner_{os.getpid()}.py"
    try:
        temp_script.write_text(clean_code, encoding="utf-8")

        # Executa usando o mesmo interpretador Python do projeto
        result = subprocess.run(
            [sys.executable, str(temp_script)],
            cwd=str(settings.WORKSPACE_DIR),
            capture_output=True,
            text=True,
            timeout=timeout
        )

        stdout = result.stdout.strip()
        stderr = result.stderr.strip()

        output = []
        if stdout:
            output.append(f"Saída (stdout):\n{stdout}")
        if stderr:
            output.append(f"Erros/Avisos (stderr):\n{stderr}")
        if not stdout and not stderr:
            output.append("Código executado com sucesso (sem saída no console).")

        return "\n\n".join(output)

    except subprocess.TimeoutExpired:
        return f"Erro: A execução do código excedeu o tempo limite de {timeout} segundos."
    except Exception as e:
        return f"Erro ao executar código Python: {str(e)}"
    finally:
        if temp_script.exists():
            try:
                temp_script.unlink()
            except Exception:
                pass
