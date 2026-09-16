# Open Grok Bot 🤖⚡

> **AI Teammates that finish the work** — Uma réplica de código aberto, modular e **100% gratuita** da plataforma **Grok Bot** ([x.ai/bot](https://x.ai/bot)).

O **Open Grok Bot** transforma modelos de inteligência artificial em uma equipe de companheiros autônomos (*AI Teammates*) com acesso a navegador, busca na web em tempo real, memória compartilhada e execução de rotinas repetíveis.

---

## 🌟 Funcionalidades Inspiradas no Grok Bot Oficial

* 🌐 **Computer Use / Navegador Autônomo**: Os bots controlam um navegador real (Playwright), acessam páginas, preenchem dados, navegam por sistemas e tiram printscreens.
* 🤝 **Connect the Bots (Multi-Agente)**: Um coordenador (**Chief of Staff**) delega trabalho entre agentes especialistas (**Researcher**, **Web Navigator**, **Sales Outbound**).
* 🧠 **Memória Compartilhada**: Todos os bots compartilham o mesmo banco de memória (SQLite) para guardar preferências de clientes, regras e contextos de projetos.
* ⚡ **Rotinas de Automação (*Show a Bot how it's done*)**: Salve tarefas recorrentes (ex: resumo diário de notícias, auditoria de sites) para os bots executarem sob demanda.
* 📱 **Controle pelo Celular e Desktop**:
  * **CLI Interativo**: Interface no terminal do computador.
  * **Bot do Telegram**: Delegue tarefas do celular (iOS / Android), receba printscreens e relatórios onde estiver.
* 💸 **100% Gratuito**: Sem pagar os $20 a $40/mês do Grok oficial. Usa **Groq Cloud (Llama 3.3 70B)** gratuito ou **Ollama** local.

---

## 🏗️ Arquitetura da Equipe de Bots

```
                             ┌───────────────────────┐
                             │     Usuário           │
                             │  (CLI ou Telegram)    │
                             └───────────┬───────────┘
                                         │
                                         ▼
                             ┌───────────────────────┐
                             │    Chief of Staff     │
                             │  (Líder / Orquestrador)│
                             └───────────┬───────────┘
                                         │
        ┌────────────────────────────────┼────────────────────────────────┐
        ▼                                ▼                                ▼
┌─────────────────┐            ┌──────────────────┐            ┌───────────────────┐
│ Researcher Bot  │            │ Web Navigator    │            │ Sales Outbound    │
│ (DuckDuckGo     │            │ (Playwright      │            │ (Prospecção &     │
│  Busca em Tempo │            │  Navegação Real  │            │  Geração de Leads │
│  Real & Notícias│            │  & Screenshots)  │            │  Personalizadas)  │
└─────────────────┘            └──────────────────┘            └───────────────────┘
        │                                │                                │
        └────────────────────────────────┴────────────────────────────────┘
                                         │
                                         ▼
                      ┌──────────────────────────────────────┐
                      │    Memória & Workspace Compartilhado │
                      │  (SQLite: Contextos, Rotinas, Files) │
                      └──────────────────────────────────────┘
```

---

## 🚀 Como Começar

### 1. Clonar e Acessar o Repositório
```bash
git clone https://github.com/seu-usuario/open-grok-bot.git
cd open-grok-bot
```

### 2. Criar e Ativar o Ambiente Virtual
```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
playwright install chromium
```

### 3. Configurar Variáveis de Ambiente
Copie o arquivo de exemplo:
```bash
cp .env.example .env
```

Abra o `.env` e adicione sua chave gratuita da Groq:
```env
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_sua_chave_aqui
```
> 💡 *Como conseguir a chave da Groq:* Acesse [console.groq.com](https://console.groq.com), crie uma conta gratuita (não precisa de cartão de crédito) e gere sua chave na aba **API Keys**.

Se quiser usar o **Telegram** para comandar o bot pelo celular:
```env
TELEGRAM_BOT_TOKEN=seu_token_do_botfather
```

---

## 💻 Como Usar

### Modo Terminal (CLI)
Inicie a interface interativa:
```bash
python run.py --cli
```

Comandos úteis dentro do CLI:
* `/help` — Exibe a lista de comandos
* `/routines` — Lista as rotinas automatizadas disponíveis
* `/run <nome_da_rotina>` — Executa uma rotina salva
* `/memory` — Visualiza memórias e regras compartilhadas
* `/files` — Lista arquivos gerados no workspace
* `/screenshot <url>` — Abre um site e salva um print na pasta `screenshots/`

### Modo Telegram (Controle Remoto)
Inicie o bot do Telegram:
```bash
python run.py --telegram
```
No Telegram, abra a conversa com seu bot e mande `/start` ou qualquer instrução de trabalho.

---

## 🛠️ Testes Automatizados

Para rodar a suíte de testes unitários:
```bash
pytest
```

---

## 📄 Licença
Este projeto é distribuído sob a licença MIT. Sinta-se livre para usar, customizar e contribuir!
