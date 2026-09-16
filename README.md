# Open Grok Bot 🤖⚡

> **AI Teammates that finish the work** — Uma réplica de código aberto, modular e **100% gratuita** da plataforma **Grok Bot** ([x.ai/bot](https://x.ai/bot)).

O **Open Grok Bot** transforma modelos de inteligência artificial em uma equipe de companheiros autônomos (*AI Teammates*) com acesso a navegador, busca na web em tempo real, memória compartilhada e execução de rotinas repetíveis.

---

## 🌟 Funcionalidades Inspiradas no Grok Bot Oficial

* 🎨 **Geração de Imagens com Flux.1**: O mesmo modelo de imagem do Grok oficial, 100% gratuito e em alta definição (1024x1024) integrado ao chat e comandos.
* 🎙️ **Transcrição de Voz com Groq Whisper**: Envie áudios e mensagens de voz pelo Telegram — o bot transcreve em ~500ms com `whisper-large-v3-turbo` e processa a tarefa direto.
* ⚡ **Gestão Proativa de Rate Limit**: Monitoramento de headers `x-ratelimit-*`, backoff com jitter e rotação de múltiplas chaves Groq para nunca bater no erro 429 (TPM).
* 🐍 **Code & Data Analyst**: Execução de scripts Python em sandbox para cálculos avançados, matemática e processamento de dados.
* 🌐 **Computer Use / Navegador Autônomo**: Os bots controlam um navegador real (Playwright), acessam páginas, preenchem formulários, navegam por sistemas e tiram screenshots.
* 🤝 **Connect the Bots (Multi-Agente)**: Um coordenador (**Chief of Staff**) orquestra especialistas (**Researcher**, **Web Navigator**, **Sales Outbound**, **Code & Data Analyst**).
* 🧠 **Memória Compartilhada & Multi-Turn**: Contexto contínuo entre sessões, lembrando regras, preferências e aprendizados passados.
* ⚡ **Rotinas de Automação (*Show a Bot how it's done*)**: Ensine o bot uma vez conversando ou salve rotinas estruturadas para rodar sob demanda com 1 clique.
* 📱 **Controle pelo Celular e Desktop**:
  * **CLI Interativo**: Interface completa com Rich no terminal.
  * **Bot do Telegram**: Menu nativo de comandos, botões interativos (Inline Keyboards), feedback de digitação contínuo (`typing` heartbeat), anti-table formatting em cartões e suporte a voz.
* 💸 **100% Gratuito**: Sem pagar os $20 a $40/mês do Grok oficial. Usa **Groq Cloud (Llama 3.3 70B & GPT-OSS)** gratuito ou **Ollama** local com fallback resiliente.

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

Comandos úteis no CLI:
* `/help` — Exibe a lista de comandos
* `/imagine <prompt>` — Gera uma imagem com Flux.1 e salva no workspace
* `/code <python_code>` — Executa código Python diretamente
* `/routines` — Lista as rotinas automatizadas disponíveis
* `/run <nome>` — Executa uma rotina salva
* `/delroutine <nome>` — Remove uma rotina
* `/memory` — Visualiza memórias e regras compartilhadas
* `/files` — Lista arquivos gerados no workspace
* `/screenshot <url>` — Abre um site e salva um print na pasta `screenshots/`
* `/reset` ou `/clear` — Limpa o histórico da sessão atual

### Modo Telegram (Controle Remoto no Celular)
Inicie o bot do Telegram:
```bash
python run.py --telegram
```
No Telegram, abra a conversa com seu bot (ex: `@Caducodesgrokbot`) e utilize:
* `/imagine <prompt>` — Cria e envia a imagem gerada com Flux.1 na hora
* `/routines` e `/run <nome>` — Gerencia e roda rotinas
* Envio de Documentos — Envie arquivos `.txt`, `.csv`, `.json`, `.py` ou `.md` para análise imediata
* Conversação Natural — Faça perguntas, solicite cotações, pesquisas na web ou navegação pelo navegador.

---

## 🛠️ Testes Automatizados

Para rodar a suíte de testes unitários:
```bash
pytest
```

---

## 📄 Licença
Este projeto é distribuído sob a licença MIT. Sinta-se livre para usar, customizar e contribuir!
