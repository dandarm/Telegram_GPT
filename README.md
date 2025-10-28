# Telegram AI Assistant Bot

Un bot Telegram basato su [python-telegram-bot](https://docs.python-telegram-bot.org/) e [OpenAI](https://platform.openai.com/), pensato per chat di gruppo con:
- memoria persistente su **file di testo** (niente DB),
- recap della chat (`/recap`),
- lavagne virtuali (`/board`),
- stato conversazionale compatto (`state.md`),
- regole anti-eco (per evitare auto-ripetizioni e allucinazioni).

## 🚀 Installazione

1. Clona il repo:
   ```bash
   git clone https://github.com/<tuo-utente>/telegram-bot.git
   cd telegram-bot
2. Crea e attiva un ambiente virtuale:
    python -m venv .venv
    source .venv/bin/activate   # Linux/macOS
    .venv\Scripts\activate      # Windows
3. Installa le dipendenze:
    pip install -r requirements.txt
4. Copia .env.example in .env:
    cp .env.example .env
5. Avvia:
    python main.py


📝 Funzioni principali

Memoria su file: per ogni chat viene creata data/<chat_id>/ con:

transcript.ndjson → log line-by-line dei messaggi

state.md → memoria strutturata (fatti, decisioni, TODO)

boards/*.md → lavagne tematiche create con /board

checkpoints/*.summary.md → riassunti salvati

Comandi disponibili

/start → messaggio di benvenuto

/mode <mention|prefix|mention_or_reply> → come il bot risponde

/prefix <prefisso> → cambia prefisso (default !ai)

/board <list|show|add> → gestisce lavagne

/recap [N] → riassume ultimi N messaggi (default 250)

/debug_context → mostra ultime righe del contesto

Risposte live: il bot risponde solo se interpellato (menzione, reply o prefisso) e usa:

ultime 10 battute utente,

state.md,

regole anti-eco.

🔒 Note su privacy

Con Group Privacy OFF il bot riceve tutti i messaggi del gruppo.

Ogni messaggio viene loggato su file in ./data/.

È bene avvisare gli utenti del gruppo che i messaggi vengono salvati per scopi di recap e memoria.

🛠 Sviluppo

Per aggiungere nuove funzioni: crea un file in app/commands/ e registra l’handler nel lifecycle.py.

Per modificare la memoria: agisci su store.py o su context_builders.py.