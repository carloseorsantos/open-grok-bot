import sys
from rich.console import Console
from rich.panel import Panel
from rich.markdown import Markdown
from rich.table import Table
from src.agents.orchestrator import chief_of_staff
from src.routines.manager import routine_manager
from src.memory.db import memory_store
from src.tools.filesystem import list_workspace_files
from src.tools.browser import browser_controller

console = Console()

BANNER = """
[bold cyan]  ___                    ____           _      ____        _   [/bold cyan]
[bold cyan] / _ \ _ __   ___ _ __  / ___|_ __ ___ | | __ | __ )  ___ | |_ [/bold cyan]
[bold cyan]| | | | '_ \ / _ \ '_ \| |  _| '__/ _ \| |/ / |  _ \ / _ \| __|[/bold cyan]
[bold cyan]| |_| | |_) |  __/ | | | |_| | | | (_) |   <  | |_) | (_) | |_ [/bold cyan]
[bold cyan] \___/| .__/ \___|_| |_|\____|_|  \___/|_|\_\ |____/ \___/ \__|[/bold cyan]
[bold cyan]      |_|                                                       [/bold cyan]
[italic dim]AI Teammates that finish the work • 100% Free & Open Source[/italic dim]
"""


def show_help():
    table = Table(title="Comandos Disponíveis", show_header=True, header_style="bold magenta")
    table.add_column("Comando", style="cyan")
    table.add_column("Descrição")
    table.add_row("/help", "Exibe esta mensagem de ajuda")
    table.add_row("/routines", "Lista as rotinas de automação disponíveis")
    table.add_row("/run <nome>", "Executa uma rotina salva")
    table.add_row("/memory", "Exibe as memórias compartilhadas entre os bots")
    table.add_row("/files", "Lista os arquivos salvos no workspace")
    table.add_row("/screenshot <url>", "Abre uma URL e salva uma captura de tela")
    table.add_row("/exit", "Encerra o Open Grok Bot")
    console.print(table)


def start_cli():
    console.print(BANNER)
    console.print(Panel(
        "[bold green]Seu time de AI Teammates está online e pronto![/bold green]\n"
        "Bots ativos: [cyan]Chief of Staff[/cyan], [yellow]Researcher[/yellow], [magenta]Web Navigator[/magenta], [blue]Sales Outbound[/blue].\n"
        "Digite sua instrução ou [bold]/help[/bold] para ver os comandos.",
        border_style="cyan"
    ))

    session_id = "cli_session"

    while True:
        try:
            user_input = console.input("\n[bold yellow]Você > [/bold yellow]").strip()
            if not user_input:
                continue

            if user_input in ("/exit", "/quit"):
                console.print("[dim]Encerrando Open Grok Bot. Até logo![/dim]")
                browser_controller.close()
                break

            elif user_input == "/help":
                show_help()

            elif user_input == "/routines":
                routines = routine_manager.list_routines()
                table = Table(title="Rotinas de Automação Salvas", show_header=True, header_style="bold green")
                table.add_column("Nome", style="cyan")
                table.add_column("Descrição")
                for r in routines:
                    table.add_row(r["name"], r["description"])
                console.print(table)

            elif user_input.startswith("/run "):
                parts = user_input[5:].strip().split(maxsplit=1)
                r_name = parts[0]
                console.print(f"[bold cyan]Executando rotina '{r_name}'...[/bold cyan]")
                with console.status("[bold green]Processando rotina com os bots...[/bold green]"):
                    res = routine_manager.run_routine(r_name)
                console.print(Panel(Markdown(res), title=f"[bold green]Resultado: {r_name}[/bold green]", border_style="green"))

            elif user_input == "/memory":
                mems = memory_store.list_memories()
                if not mems:
                    console.print("[yellow]Nenhuma memória salva ainda.[/yellow]")
                else:
                    table = Table(title="Memórias Compartilhadas", show_header=True, header_style="bold yellow")
                    table.add_column("Categoria", style="magenta")
                    table.add_column("Chave", style="cyan")
                    table.add_column("Valor")
                    for m in mems:
                        table.add_row(m["category"], m["key"], str(m["value"]))
                    console.print(table)

            elif user_input == "/files":
                console.print(Panel(list_workspace_files(), title="Workspace Files", border_style="blue"))

            elif user_input.startswith("/screenshot "):
                url = user_input[12:].strip()
                console.print(f"[dim]Navegando para {url}...[/dim]")
                browser_controller.navigate(url)
                shot_path = browser_controller.take_screenshot("quick_shot.png")
                console.print(f"[green]{shot_path}[/green]")

            else:
                # Enviar para o Chief of Staff
                with console.status("[bold cyan]Chief of Staff coordenando os bots...[/bold cyan]"):
                    response = chief_of_staff.run(user_input, session_id=session_id)
                console.print(Panel(Markdown(response), title="[bold cyan]Chief of Staff[/bold cyan]", border_style="cyan"))

        except (KeyboardInterrupt, EOFError):
            console.print("\n[dim]Saindo...[/dim]")
            browser_controller.close()
            break
        except Exception as e:
            console.print(f"[bold red]Erro inesperado:[/bold red] {e}")


if __name__ == "__main__":
    start_cli()
