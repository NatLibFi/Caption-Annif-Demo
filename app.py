import gradio as gr
import requests
from annif_client import AnnifClient
import os
import io
import base64


# Get VLM API base URL and API key from environment variables
VLM_API_BASE_URL = os.getenv("VLM_API_BASE_URL")
if not VLM_API_BASE_URL:
    raise RuntimeError("VLM_API_BASE_URL environment variable must be set.")
VLM_API_KEY = os.getenv("VLM_API_KEY", "")
VLM_API_ENDPOINT = f"{VLM_API_BASE_URL}/v1/chat/completions"


# Get Annif API base URL from environment variable, fallback to default
ANNIF_API_BASE_URL = os.getenv("ANNIF_API_BASE_URL")
if ANNIF_API_BASE_URL:
    if not ANNIF_API_BASE_URL.endswith("v1/"):
        raise RuntimeError("ANNIF_API_BASE_URL should end with 'v1/'")
    annif = AnnifClient(api_base=ANNIF_API_BASE_URL)
else:
    annif = AnnifClient()


def get_caption(image, prompt):
    # Convert image to base64 JPEG

    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    # Prepare payload for VLM (OpenAI schema)
    payload = {
        "model": "gemma3",
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {"url": f"data:image/jpeg;base64,{img_b64}"},
                    },
                ],
            }
        ],
        "max_tokens": 300,
    }
    headers = {"X-API-Key": VLM_API_KEY} if VLM_API_KEY else {}
    try:
        response = requests.post(VLM_API_ENDPOINT, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()
        # Assume caption is in data['choices'][0]['message']['content']
        caption = data["choices"][0]["message"]["content"]
    except Exception as e:
        print(f"VLM API error: {e}")  # Detailed error for admin
        raise gr.Error("Sorry, there was a problem generating a caption.")
    return caption


def get_subjects(caption, project_id):
    try:
        results = annif.suggest(project_id=project_id, text=caption)
        label_scores = {result["label"]: result["score"] for result in results}
        if not label_scores:
            return {}
        return label_scores
    except Exception as e:
        print(f"Annif API error: {e}")  # Detailed error for admin
        raise gr.Error("Sorry, there was a problem getting subject suggestions.")


with gr.Blocks(title="VLM Caption & Annif Demo") as demo:
    gr.Markdown("# VLM Caption & Annif Demo")
    gr.Markdown(
        """
    **How it works:**
    1. Upload or take a photo in the input section below.
    2. The image is sent to a Visual Language Model to generate a caption.
    3. [Annif](https://github.com/NatLibFi/Annif) suggests subjects based on the caption via the API of [Finto AI](https://ai.finto.fi).
    """
    )
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Input")
            image_input = gr.Image(
                type="pil",
                label="Image Input (upload or take a photo)",
                webcam_options=gr.WebcamOptions(mirror=False),
            )
            language_dropdown = gr.Dropdown(
                choices=[("Finnish", "fi"), ("Swedish", "sv"), ("English", "en")],
                value="fi",
                label="Output Language",
                info="Select the output language for caption and subject suggestions",
            )
            project_dropdown = gr.Dropdown(
                choices=[
                    ("YSO - General Finnish Ontology", "yso"),
                    ("YKL - Finnish Public Library Classification ", "ykl"),
                    ("KAUNO - Ontology for Fiction (for Finnish only)", "kauno"),
                ],
                value="yso",
                label="Annif Project",
                info="Select the vocabulary from where subject suggestions are drawn "\
                    "([YSO](https://finto.fi/yso/), [YKL](https://finto.fi/ykl/), [KAUNO](https://finto.fi/kauno/))",
            )
            with gr.Accordion("VLM Prompt", open=False):
                prompt_input = gr.Textbox(
                    label="",
                    lines=8,
                    info="Edit the prompt used to generate the caption. The language of the prompt should match the selected output language.",
                )
            submit_btn = gr.Button("Submit", interactive=False)
            clear_btn = gr.Button("Clear")
        with gr.Column():
            gr.Markdown("### Output")
            caption_output = gr.Textbox(label="Caption", lines=10, interactive=False)
            subjects_output = gr.Label(label="Subject Suggestions", show_heading=False)

    # Translated prompts for VLM
    VLM_PROMPTS = {
        "fi": (
            "Luo vaihtoehtoinen tekstikuvaus, joka on tarkoitettu henkilöille, jotka eivät näe kuvaa. "
            "Kuvaile kuvan todellista sisältöä, älä tulkitse mitään. "
            "Aloita yleisellä kuvauksella ja siirry sitten yksityiskohtiin. "
            "Kuvaile yksityiskohtia ainakin viiden lauseen verran. "
            "Jos kuvassa näkyy tekstiä, kerro mitä siinä lukee ja jos teksti ei ole suomea, käännä se myös suomeksi. "
            'Vastaa vain lopullisella alt-tekstillä, älä lisää "tässä on alt-teksti", selityksiä tai väliotsikoita. '
            "Vastaa suomeksi."
        ),
        "en": (
            "Create an alternative text description for people who cannot see the image. "
            "Describe the actual content of the image, do not interpret anything. "
            "Start with a general description and then move to details. "
            "Describe details in at least five sentences. "
            "If there is text in the image, state what it says and translate it into English if it is not in English. "
            "Respond only with the final alt text, do not add explanations or headings."
        ),
        "sv": (
            "Skapa en alternativ textbeskrivning för personer som inte kan se bilden. "
            "Beskriv bildens faktiska innehåll, tolka ingenting. "
            "Börja med en allmän beskrivning och gå sedan vidare till detaljer. "
            "Beskriv detaljerna med minst fem meningar. "
            "Om det finns text i bilden, ange vad det står och översätt det till svenska om det inte är på svenska. "
            "Svara endast med den slutliga alt-texten, lägg inte till förklaringar eller rubriker."
        ),
    }

    def run_app(image, custom_prompt, language, project):
        # Use custom prompt if provided, otherwise use default prompt for selected language
        prompt = custom_prompt.strip() if custom_prompt.strip() else VLM_PROMPTS.get(language, VLM_PROMPTS["fi"])
        # Compose Annif project identifier
        project_id = f"{project}-{language}"
        caption = get_caption(image, prompt)
        try:
            subjects = get_subjects(caption, project_id)
            return caption, subjects
        except gr.Error:
            gr.Warning("Sorry, there was a problem getting subject suggestions.")
            return caption, {}

    submit_btn.click(
        run_app,
        inputs=[image_input, prompt_input, language_dropdown, project_dropdown],
        outputs=[caption_output, subjects_output],
    )
    clear_btn.click(lambda: ("", ""), outputs=[caption_output, prompt_input])

    def update_submit_btn(img):
        return gr.update(interactive=img is not None)

    image_input.upload(update_submit_btn, inputs=image_input, outputs=submit_btn)

    def update_prompt_from_language(lang):
        """Update the prompt textarea when language changes"""
        default_prompt = VLM_PROMPTS.get(lang, VLM_PROMPTS["fi"])
        return gr.update(value=default_prompt)

    language_dropdown.change(update_prompt_from_language, inputs=language_dropdown, outputs=prompt_input)

    # Set initial prompt value based on default language (fi)
    def set_initial_values():
        return update_prompt_from_language("fi")

    demo.load(fn=set_initial_values, outputs=prompt_input)

    demo.launch()
