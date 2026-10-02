import json
import os

CODEX_PATH = "codex.json"

def load_codex_profile(role: str) -> dict:
    """Loads profile configurations for a given role from codex or returns default parameters."""
    try:
        if os.path.exists(CODEX_PATH):
            with open(CODEX_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get(role, {"temperature": 0.7})
    except Exception:
        pass
    
    # Default fallbacks per role
    defaults = {
        "R&R": {"temperature": 0.5},
        "TriCore": {"temperature": 0.7},
        "Triformer": {"temperature": 0.9}
    }
    return defaults.get(role, {"temperature": 0.7})
