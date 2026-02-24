# analyzer.py
import json
import re
import yaml

# ---------------------------------------------------------------------------
# Customize this to call your webui model. Replace stub with actual call.
# ---------------------------------------------------------------------------

# Uses the web UI's OpenAI-compatible /v1/chat/completions endpoint
import requests

def call_model(prompt, max_tokens=512, temperature=0.7):
    url = "http://127.0.0.1:5000/v1/chat/completions"
    payload = {
        "model": "default",  # or specify your model name if needed
        "messages": [
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        "max_tokens": max_tokens,
        "temperature": temperature
    }
    response = requests.post(url, json=payload)
    response.raise_for_status()
    return response.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Default / empty bio structure
# ---------------------------------------------------------------------------
DEFAULT_BIO = {
    "name": "",
    "alias": "",
    "age": "",
    "appearance": "",
    "origin": "",
    "occupation": "",
    "personality": ["cold", "blunt", "closed"],
    "kinks": [],
    "fetishes": [],
}

BIO_FILE = "user_bio.yaml"


# ---------------------------------------------------------------------------
# Bio I/O helpers
# ---------------------------------------------------------------------------

def load_bio(path: str = BIO_FILE) -> dict:
    """Load the user bio YAML file and return it as a dict."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
        # Support both a bare mapping and {user_bio: <yaml-string>} wrapper
        if isinstance(data, dict) and "user_bio" in data:
            inner = data["user_bio"]
            if isinstance(inner, str):
                data = yaml.safe_load(inner)
            else:
                data = inner
        return data or {}
    except FileNotFoundError:
        return dict(DEFAULT_BIO)


def save_bio(bio: dict, path: str = BIO_FILE) -> None:
    """Save the bio dict back to YAML, wrapped in the user_bio key."""
    # Serialise inner bio as a YAML string so the format matches the original
    inner_str = yaml.dump(bio, allow_unicode=True, default_flow_style=False)
    wrapper = {"user_bio": inner_str}
    with open(path, "w", encoding="utf-8") as f:
        yaml.dump(wrapper, f, allow_unicode=True, default_flow_style=False)


def bio_to_readable_string(bio: dict) -> str:
    """Convert bio dict to a compact readable string for the prompt."""
    return yaml.dump(bio, allow_unicode=True, default_flow_style=False)


# ---------------------------------------------------------------------------
# Prompt
# ---------------------------------------------------------------------------

PROMPT_TEMPLATE = """
You analyze a roleplay chat transcript and update a user bio written in YAML.

Rules:
- Treat the chat as in-character roleplay.
- Output ONLY valid JSON — no prose, no markdown fences.
- Return a single object with these optional keys (only include a key if you
  have something new / changed to set):
    name        (string)
    alias       (string)
    age         (string)
    appearance  (string)
    origin      (string)
    occupation  (string)
    personality (array of short trait phrases)
    kinks       (array of short phrases)
    fetishes    (array of short phrases)
- For LIST fields (personality / kinks / fetishes) return ONLY the NEW items
  to append — do NOT repeat items already in the bio.
- For STRING fields return the full updated value only if it changed.
- If nothing new can be inferred, return an empty object: {{}}
- No speculation; only infer if strongly implied by the transcript.

Current bio:
{current_bio}

Transcript:
{transcript}

Return JSON now.
"""


def build_prompt(transcript: str, bio: dict) -> str:
    return PROMPT_TEMPLATE.format(
        transcript=transcript,
        current_bio=bio_to_readable_string(bio),
    )


# ---------------------------------------------------------------------------
# JSON parsing
# ---------------------------------------------------------------------------

def parse_json_from_model(text: str) -> dict:
    """Extract and parse a JSON object from potentially noisy model output."""
    match = re.search(r"(\{(?:.|\n)*\})", text.strip())
    if match:
        raw = match.group(1)
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            cleaned = re.sub(r",\s*}", "}", raw)
            cleaned = re.sub(r",\s*\]", "]", cleaned)
            return json.loads(cleaned)
    raise ValueError("Could not parse JSON from model output.")


# ---------------------------------------------------------------------------
# Bio merging
# ---------------------------------------------------------------------------

LIST_FIELDS = {"personality", "kinks", "fetishes"}
STRING_FIELDS = {"name", "alias", "age", "appearance", "origin", "occupation"}


def merge_bio(current: dict, additions: dict) -> dict:
    """Merge model additions into the current bio dict."""
    updated = dict(current)

    for field in STRING_FIELDS:
        if field in additions and additions[field]:
            updated[field] = additions[field]

    for field in LIST_FIELDS:
        if field in additions and additions[field]:
            existing = set(updated.get(field) or [])
            new_items = [item for item in additions[field] if item not in existing]
            updated[field] = list(updated.get(field) or []) + new_items

    return updated


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def update_bio_from_chat(chat_transcript_text: str, bio_path: str = BIO_FILE) -> dict:
    """
    Main entry point.
    Reads the bio, runs inference, merges additions, saves, and returns the
    updated bio dict.
    """
    bio = load_bio(bio_path)
    prompt = build_prompt(chat_transcript_text, bio)
    raw_output = call_model(prompt)
    additions = parse_json_from_model(raw_output)

    if not additions:
        print("[analyzer] No new bio additions inferred.")
        return bio

    updated_bio = merge_bio(bio, additions)
    save_bio(updated_bio, bio_path)
    print(f"[analyzer] Bio updated with: {additions}")
    return updated_bio


# ---------------------------------------------------------------------------
# Backwards-compat alias
# ---------------------------------------------------------------------------

def generate_recommendations_from_chat(chat_transcript_text: str) -> dict:
    """Legacy name — wraps update_bio_from_chat without saving."""
    bio = load_bio()
    prompt = build_prompt(chat_transcript_text, bio)
    raw_output = call_model(prompt)
    return parse_json_from_model(raw_output)
