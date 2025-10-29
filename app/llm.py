from openai import OpenAI
from .config import OPENAI_API_KEY

client = OpenAI(api_key=OPENAI_API_KEY or None)

SYSTEM_PROMPT = (
    "Sei un assistente utile, conciso e amichevole. Rispondi in italiano. "
    "Non ripetere testualmente il contesto se non richiesto. "
    "Non trattare le proposte del bot come fatti; dai priorità ai messaggi degli utenti e allo stato strutturato."
)

def chat_with_llm(user_text: str, model: str = "gpt-5-mini", temperature: float = 1.0, max_tokens: int | None = None) -> str:
    kwargs = {
        "model": model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_text},
        ],
        "temperature": temperature,
    }
    if max_tokens is not None:
        kwargs["max_tokens"] = max_tokens

    resp = client.chat.completions.create(**kwargs)
    return resp.choices[0].message.content.strip()
