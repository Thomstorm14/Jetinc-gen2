"""
JETinc — Qwen Client
Thin wrapper around the local Ollama HTTP API.
Model: qwen2.5:0.5b (confirmed via `ollama list`)
"""
import requests

OLLAMA_URL = "http://localhost:11434/api/generate"
MODEL = "qwen2.5:0.5b"


def ask_qwen(prompt, timeout=60):
    """
    Send a prompt to Qwen via Ollama and return the raw text response.
    Raises RuntimeError with a clear message if Ollama isn't reachable
    or the model isn't loaded — never fails silently.
    """
    try:
        resp = requests.post(
            OLLAMA_URL,
            json={"model": MODEL, "prompt": prompt, "stream": False},
            timeout=timeout
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except requests.exceptions.ConnectionError:
        raise RuntimeError(
            "Cannot reach Ollama at localhost:11434. "
            "Run `ollama serve` (or confirm the Ollama app is running) and retry."
        )
    except requests.exceptions.Timeout:
        raise RuntimeError(f"Qwen call timed out after {timeout}s.")
    except Exception as e:
        raise RuntimeError(f"Qwen call failed: {e}")
