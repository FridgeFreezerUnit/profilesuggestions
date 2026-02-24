# profile.py
from modules import shared
from modules.shared import save_settings

def get_user_bio():
    return shared.settings.get("user_bio", "")

def set_user_bio(new_bio):
    shared.settings["user_bio"] = new_bio
    save_settings()

def merge_user_bio(additions):
    """
    additions: list[str] or str
    Merges without overwriting existing content.
    """
    current = get_user_bio()

    if isinstance(additions, list):
        additions = ", ".join(additions)

    if additions.lower() in current.lower():
        return current  # already present

    updated = current.strip()
    if updated:
        updated += "; "
    updated += additions

    set_user_bio(updated)
    return updated