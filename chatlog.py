# chatlog.py
import json
from pathlib import Path

# Adjust this path if your webui stores sessions somewhere else
DEFAULT_CHATLOG_PATHS = [
    Path("chat_logs/session_history.json"),
    Path("sessions/latest_chat.json"),
]

def load_chatlog_from_file():
    for p in DEFAULT_CHATLOG_PATHS:
        if p.exists():
            return json.loads(p.read_text(encoding="utf-8"))
    return None

def format_chat_for_prompt(chat):
    """
    Accept chat as a list of {"role": "user|assistant|system", "content": "..."}
    Returns a plain text transcript suitable for model input.
    """
    lines = []
    for m in chat:
        role = m.get("role", "user")
        text = m.get("content", "")
        lines.append(f"[{role.upper()}] {text}")
    return "\n".join(lines)