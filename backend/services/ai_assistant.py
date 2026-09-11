import json
from groq import Groq

PREFERRED_MODELS = [
    "groq/compound",
    "groq/compound-mini",
    "llama-3.3-70b-versatile",
    "qwen/qwen3.6-27b"
]

def ask_groq_assistant(question: str, compact_context: dict, api_key: str) -> str:
    """Send the question + model context to Groq and return the answer text."""
    if not api_key or not api_key.strip():
        return "⚠️ No GROQ_API_KEY provided. Please set GROQ_API_KEY in your backend/.env configuration."

    try:
        client = Groq(api_key=api_key.strip())

        system_prompt = (
            "You are ArchiShield's model assistant. Answer using ONLY the JSON data below. "
            "Use real numbers from it. If data is insufficient, say so. "
            "Keep answers to 2-5 sentences plus bullets if helpful. "
            "Never invent names, counts, or properties not in the data.\n\n"
            f"DATA:\n{json.dumps(compact_context, separators=(',', ':'))}"
        )

        last_error = None
        for model in PREFERRED_MODELS:
            try:
                response = client.chat.completions.create(
                    model=model,
                    max_tokens=500,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": question},
                    ],
                )
                return response.choices[0].message.content
            except Exception as me:
                last_error = me
                err_text = str(me).lower()
                # If it's a 401 auth error, fail immediately (do not retry other models)
                if "401" in err_text or "invalid_api_key" in err_text or "expired_api_key" in err_text or "invalid api key" in err_text:
                    return ("⚠️ Groq API key is invalid or expired. "
                            "Please replace GROQ_API_KEY in backend/.env with a valid Groq API key.")
                # If model is 404/not found, loop to next preferred model
                continue

        if last_error:
            raise last_error

    except Exception as e:
        err_str = str(e)
        if "401" in err_str or "invalid_api_key" in err_str.lower() or "expired_api_key" in err_str.lower() or "invalid api key" in err_str.lower():
            return ("⚠️ Groq API key is invalid or expired. "
                    "Please replace GROQ_API_KEY in backend/.env with a valid Groq API key.")
        if "413" in err_str or "too large" in err_str.lower() or "rate_limit" in err_str.lower():
            return ("⚠️ The model context is too large for the free Groq tier's limits. "
                    "Try asking a more specific question (e.g., about one floor or element type).")
        return f"⚠️ Groq API error: {e}"

    return "⚠️ Groq API request could not be completed."
