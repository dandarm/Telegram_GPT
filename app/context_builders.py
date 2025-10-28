from .store import FileStore
from .llm import chat_with_llm

ANTI_ECHO_RULES = (
    "Regole anti-eco:\n"
    "1) Non ripetere testualmente il contesto.\n"
    "2) Non trattare come fatti le proposte del bot.\n"
    "3) Dai priorità a: (a) messaggi utenti, (b) stato strutturato.\n"
    "4) Se mancano info, chiedi chiarimenti brevi.\n"
)

def build_live_prompt(store: FileStore, user_now: str, text_now: str, max_user_lines: int = 10) -> str:
    recent = [r for r in store.tail_msgs(80) if r["is_bot"] == 0]
    window = recent[-max_user_lines:]
    transcript_lines = [f'{r["user"] or "utente"}: {r["text"]}' for r in window]
    state = store.read_state()

    prompt = (
        "Sei un assistente in una chat di gruppo.\n" + ANTI_ECHO_RULES + "\n\n"
        "=== STATO (estratto strutturato) ===\n" + state + "\n\n"
        "=== CONTESTO RECENTE (solo utenti) ===\n" + "\n".join(transcript_lines) +
        "\n\n=== MESSAGGIO CORRENTE ===\n" + f"{user_now}: {text_now}\n\n=== RISPOSTA ==="
    )
    return prompt

def update_state_from_exchange(store: FileStore, last_user: str, user_text: str, bot_text: str) -> None:
    state = store.read_state()
    prompt = (
        "Aggiorna lo STATO in modo minimale e coerente.\n"
        "Mantieni sezioni: Fatti, Decisioni, Vincoli, TODO, Punti aperti.\n"
        "Integra SOLO nuovi elementi/turni recenti. Evita ridondanza.\n\n"
        f"=== STATO ATTUALE ===\n{state}\n\n"
        "=== ULTIMO SCAMBIO ===\n"
        f"UTENTE ({last_user}): {user_text}\nBOT: {bot_text}\n\n=== NUOVO STATO ==="
    )
    new_state = chat_with_llm(prompt)
    store.write_state(new_state)
