
---

# 📄 AGENTS.md

```markdown
# AGENTS — Note operative per sviluppatori e agenti AI

Questo file serve a chi mantiene o estende il codice, inclusi strumenti come Codex.

## Architettura a moduli

- **app/config.py**
  - Legge variabili d'ambiente da `.env`.
  - Parametri principali: `TELEGRAM_BOT_TOKEN`, `OPENAI_API_KEY`, `DEFAULT_MODE`, `DEFAULT_PREFIX`.

- **app/store.py**
  - Gestisce lo storage su file.
  - Ogni chat ha una directory `./data/<chat_id>/`.
  - Metodi chiave:
    - `append_msg(user, text, is_bot)` → aggiunge riga JSON a `transcript.ndjson`.
    - `tail_msgs(max_lines)` → ultime N righe del transcript.
    - `read_state()/write_state()` → stato strutturato (`state.md`).
    - `append_board(name, text)` → aggiunge a una lavagna in `boards/`.

- **app/llm.py**
  - Wrapper sync su OpenAI Chat Completions.
  - Funzione: `chat_with_llm(prompt, model="gpt-4o-mini")`.

- **app/filters.py**
  - Determina quando il bot deve rispondere:
    - menzione,
    - reply,
    - prefisso.
  - `is_addressed()` → ritorna True/False.

- **app/context_builders.py**
  - Costruisce i prompt per il modello.
  - `build_live_prompt(...)` → compone prompt con:
    - `state.md`,
    - ultime X righe di utenti,
    - messaggio corrente.
  - `update_state_from_exchange(...)` → aggiorna `state.md` dopo ogni risposta del bot.

- **app/handlers.py**
  - Entry point per messaggi e comandi base.
  - `handle_message()`:
    - logga il messaggio,
    - aggiorna transcript,
    - controlla `is_addressed`,
    - costruisce il prompt,
    - chiama LLM,
    - logga la risposta,
    - aggiorna `state.md`.
  - `reply_and_log()` → invia chunk di testo e aggiunge al transcript.

- **app/commands/**
  - `boards.py`: implementa `/board`.
  - `recap.py`: implementa `/recap`.

- **app/lifecycle.py**
  - Gestisce avvio/arresto con notifiche opzionali in `ADMIN_CHAT_ID`.
  - Avvio manuale di Application (`initialize`, `start`, `start_polling`).

- **main.py**
  - Punto d’ingresso. Lancia `asyncio.run(run())`.

## Estendere il bot

- **Nuovi comandi**: crea un file `app/commands/tuo.py` con una funzione `register(app)` che aggiunge l’handler.
- **Nuova memoria**: puoi cambiare `store.py` per usare formati diversi (es. JSON aggregati, markdown).
- **Nuovi LLM**: cambia `llm.py` (puoi sostituire OpenAI con altro provider).

## Anti-eco & Allucinazioni

- Le risposte del bot **non vanno riutilizzate testualmente** come contesto.
- Vanno invece:
  - salvate nel `transcript.ndjson` per recap,
  - compattate in `state.md` (estrazione di fatti e decisioni).
- Questo design evita che il bot si auto-confermi o amplifichi errori.

## File di dati

- **Transcript**: NDJSON append-only.
- **State**: file markdown editato dal bot (idempotente).
- **Boards**: lavagne tematiche in markdown.
- **Checkpoints**: riassunti snapshot periodici.

## Debug & Testing

- `/debug_context` → mostra ultime 10 righe viste dal bot.
- Log livello INFO: messaggi ricevuti `[RX] ...`.

---
