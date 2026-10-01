"""
JETinc — Ollama Client (Gemma 3 4B)
Thin wrapper around the local Ollama HTTP API.
Model: gemma3:4b (confirmed via `ollama list`)

Configured with keep_alive (keeps model resident in memory between
calls instead of reloading from disk each time) and num_predict
(hard cap on response length, since prompts ask for brevity).
"""
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "gemma3:4b"


def ask_qwen(prompt, timeout=60, max_tokens=200):
    """
    Send a prompt to Gemma 3 4B via Ollama and return the raw text response.
    Maintains `ask_qwen` function signature for compatibility with genone callers.
    Raises RuntimeError with a clear message if Ollama isn't reachable
    or the model isn't loaded — never fails silently.
    """
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={
                "model": MODEL,
                "prompt": prompt,
                "stream": False,
                "keep_alive": "30m",
                "options": {
                    "num_predict": max_tokens,
                },
            },
            timeout=timeout,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot reach Ollama at localhost:11434. "
            "Run `ollama serve` (or confirm the Ollama app is running) and retry."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Gemma call timed out after {timeout}s.")
    except Exception as e:
        raise RuntimeError(f"Gemma call failed: {e}")


# Alias for explicit naming
ask_gemma = ask_qwen
