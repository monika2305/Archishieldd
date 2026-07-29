import json
from groq import Groq

def ask_groq_assistant(question: str, compact_context: dict, api_key: str) -> str:
    """Send the question + model context to Groq and return the answer text."""
    if not api_key:
        return "⚠️ No GROQ_API_KEY provided. Please set it in your .env configuration."

    try:
        client = Groq(api_key=api_key)

        system_prompt = (
            "You are ArchiShield's model assistant. Answer using ONLY the JSON data below. "
            "Use real numbers from it. If data is insufficient, say so. "
            "Keep answers to 2-5 sentences plus bullets if helpful. "
            "Never invent names, counts, or properties not in the data.\n\n"
            f"DATA:\n{json.dumps(compact_context, separators=(',', ':'))}"
        )

        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            max_tokens=500,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": question},
            ],
        )
        return response.choices[0].message.content
    except Exception as e:
        err_str = str(e)
        if "413" in err_str or "too large" in err_str.lower() or "rate_limit" in err_str.lower():
            return ("⚠️ The model is too large for the free Groq tier's limits. "
                    "Try asking a more specific question (e.g., about one floor or element type).")
        return f"⚠️ Groq API error: {e}"
