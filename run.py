import argparse
import sys


def main():
    parser = argparse.ArgumentParser(description="Open Grok Bot - AI Teammates Open Source e Gratuito")
    parser.add_argument(
        "--cli",
        action="store_true",
        default=True,
        help="Inicia a interface de terminal interativa (padrão)"
    )
    parser.add_argument(
        "--telegram",
        action="store_true",
        help="Inicia o bot do Telegram para controle remoto"
    )

    args, unknown = parser.parse_known_args()

    if args.telegram:
        from src.interfaces.telegram_bot import run_telegram_bot
        run_telegram_bot()
    else:
        from src.interfaces.cli import start_cli
        start_cli()


if __name__ == "__main__":
    main()
