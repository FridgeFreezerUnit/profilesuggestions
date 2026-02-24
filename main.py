# main.py
import gradio as gr
from .profile import load_profile, save_profile, apply_updates
from .chatlog import load_chatlog_from_file, format_chat_for_prompt
from .analyzer import generate_recommendations_from_chat

def analyze_and_preview():
    # 1) load chat (try file)
    chat = load_chatlog_from_file()
    if chat:
        transcript = format_chat_for_prompt(chat)
    else:
        transcript = "NO_CHAT_FOUND"  # you may allow pasting one in the UI

    try:
        rec = generate_recommendations_from_chat(transcript)
    except Exception as e:
        return {"error": str(e)}

    # Format recommendations for UI
    return rec

def apply_selected_updates(profile, recommendations, selected_keys):
    # recommendations expected as dict from model
    updates = {k: recommendations[k] for k in selected_keys}
    new_profile, diff = apply_updates(profile, updates)
    save_profile(new_profile)
    return new_profile, json_to_md(diff)

def json_to_md(d):
    md_lines = []
    for k, v in d.items():
        md_lines.append(f"### {k}\n**Before:** `{v['before']}`\n**After:** `{v['after']}`\n")
    return "\n".join(md_lines)

def setup():
    profile = load_profile()

    with gr.Blocks() as demo:
        gr.Markdown("## Roleplay-based Profile Recommender")

        with gr.Row():
            profile_box = gr.JSON(value=profile, label="Loaded profile", interactive=False)
            rec_box = gr.JSON(value={}, label="Model recommendations", interactive=False)

        with gr.Row():
            analyze_btn = gr.Button("Analyze roleplay & recommend")
            apply_btn = gr.Button("Apply selected updates")
            selected_keys = gr.CheckboxGroup(choices=[], label="Select which fields to apply")

        status = gr.Markdown()

        def on_analyze():
            rec = analyze_and_preview()
            if "error" in rec:
                status.update(f"❌ Error: {rec['error']}")
                return profile, {}
            # present recommendations and fill choices
            keys = list(rec.keys())
            selected_keys.update(choices=keys, value=keys)  # default select all
            rec_box.update(value=rec)
            return load_profile(), rec

        analyze_btn.click(on_analyze, outputs=[profile_box, rec_box])

        # Note: we pass selected_keys value to apply; in real Gradio you should wire inputs properly
        def on_apply(rec):
            p = load_profile()
            selections = selected_keys.value or []
            newp, diffmd = apply_selected_updates(p, rec, selections)
            status.update("✅ Profile updated")
            profile_box.update(value=newp)
            return newp, diffmd

        apply_btn.click(lambda rec: on_apply(rec), inputs=[rec_box], outputs=[profile_box, status])

    return demo

# the webui will call setup() on extension load
def setup_extension():
    return setup()