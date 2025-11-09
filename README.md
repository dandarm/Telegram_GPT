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

## 🗓 Riassunto giornaliero automatico

Il bot può generare automaticamente un *riassunto del giorno* chiedendo a Codex di analizzare l’intera knowledge base (cartella `data/`) e inoltrare l’output in tutte le chat note. Attiva la funzione con le variabili d’ambiente:

- `DAILY_SUMMARY_ENABLED=1` abilita il job (default disabilitato).
- `DAILY_SUMMARY_TIME=HH:MM` imposta l’orario locale (default `00:00`).
- `DAILY_SUMMARY_REPO` indica la root del progetto da cui lanciare `codex exec` (default: repo corrente).
- `DAILY_SUMMARY_OUTPUT_FILE` file in cui Codex scrive l’ultimo messaggio (default `data/daily_summary_last.txt`).
- `DAILY_SUMMARY_PROMPT` consente di personalizzare il prompt passato a Codex.
- `DAILY_SUMMARY_MAX_WORDS` limita il numero massimo di parole nel riassunto (default `400`).
- `DAILY_SUMMARY_LOOKBACK_HOURS` definisce quante ore di transcript considerare (default `24`).
- `DAILY_SUMMARY_SCOPE_DIR` directory dove vengono generati gli estratti temporanei (default `data/_daily_summary_scope`).

Prima di chiamare Codex il bot crea automaticamente `DAILY_SUMMARY_SCOPE_DIR`, copiando gli `state.md` e solo i messaggi delle ultime `DAILY_SUMMARY_LOOKBACK_HOURS` ore (per ridurre il carico). La procedura esegue `codex exec ... --output-last-message <file> -- "<prompt>"`, legge il file generato e manda il contenuto (preceduto da “📝 Riassunto del giorno”) in tutte le chat registrate. Ad ogni esecuzione viene creato anche un file con suffisso `_YYYYMMDD` accanto al percorso configurato per conservare lo storico. Assicurati che la CLI `codex` sia installata e raggiungibile nel `PATH`.
