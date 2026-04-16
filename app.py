import gradio as gr
import requests
from annif_client import AnnifClient
import os
import io
import base64
from PIL import Image


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
    # If image is a filepath (str), open it as a PIL Image
    if isinstance(image, str):
        image = Image.open(image)

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
    4. The prompt that instructs the VLM can be customized in the "VLM Prompt" section below.
    """
    )
    with gr.Row():
        with gr.Column():
            gr.Markdown("### Input")
            image_input = gr.Image(
                type="filepath",
                label="Image Input (upload or take a photo)",
                webcam_options=gr.WebcamOptions(mirror=False),
                height=420,
            )
            credit_display = gr.Markdown(value="", visible=True)

            # Credit mapping for example images
            images = {
                "examples/snowman-poster.jpg": "Image: Osmo K. Oksanen, provided by the Finnish Railway Museum, https://finna.fi/Record/srm.166912837857100",
                "examples/hus-4423.jpg": "Image: Aarne Pietinen, provided by HUS Helsinki University Hospital, https://finna.fi/Record/husmuseo.hus-4423",
                "examples/pjotr-kropotkin.jpg": "Image: Mia Green, provided by the Museum of Torne Valley, https://finna.fi/Record/tornionlaakso.4294dd9d-998f-4c2a-9b20-63b945bccdcc",
                "examples/spider-web.jpg": "Image: Merja Wesander, provided by the Helsinki City Museum, https://finna.fi/Record/hkm.8b0047a2-8c39-4376-bc95-7a9988cb36e0",
                "examples/flower-and-bee.jpg": "Image: Juho Inkinen",
            }
            example_keys = list(images.keys())
            examples_component = gr.Examples(
                examples=example_keys,
                inputs=image_input,
                label="Example Images",
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
                info="Select the vocabulary from where subject suggestions are drawn "
                "([YSO](https://finto.fi/yso/), [YKL](https://finto.fi/ykl/), [KAUNO](https://finto.fi/kauno/))",
            )
            with gr.Accordion("VLM Prompt", open=False):
                prompt_input = gr.Textbox(
                    label="",
                    lines=8,
                    info="Edit the prompt used to generate the caption. The language of the prompt should match the selected output language.",
                )
            submit_btn = gr.Button("Submit")
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
        if image is None:
            raise gr.Error("Please upload or select an image first.")
        # Use custom prompt if provided, otherwise use default prompt for selected language
        prompt = (
            custom_prompt.strip()
            if custom_prompt.strip()
            else VLM_PROMPTS.get(language, VLM_PROMPTS["fi"])
        )
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
    clear_btn.click(lambda: ("", {}), outputs=[caption_output, subjects_output])

    def update_prompt_from_language(lang):
        """Update the prompt textarea when language changes"""
        default_prompt = VLM_PROMPTS.get(lang, VLM_PROMPTS["fi"])
        return gr.update(value=default_prompt)

    language_dropdown.change(
        update_prompt_from_language, inputs=language_dropdown, outputs=prompt_input
    )

    # Set initial prompt value based on default language (fi)
    def set_initial_values():
        return update_prompt_from_language("fi")

    demo.load(fn=set_initial_values, outputs=prompt_input)

    # Update credit display when example is selected
    def update_credit_from_image(img):
        # Gradio with type="filepath" passes a string path
        if isinstance(img, str):
            filename = os.path.basename(img)
            credit = images.get(f"examples/{filename}", "")
            return f"*{credit}*" if credit else ""
        # Pass PIL Image objects (from webcam or other sources)
        return ""

    # .upload() fires after a user file is fully uploaded — no pending-upload warning.
    # .clear() resets the credit when the image is removed.
    image_input.upload(
        update_credit_from_image, inputs=image_input, outputs=credit_display
    )
    image_input.clear(lambda: "", outputs=credit_display)

    # Handle example image selection via the Examples dataset click event.
    # This avoids using image_input.change(), which fires mid-upload and causes
    # the "Waiting for file(s) to finish uploading" warning.
    credits_list = [f"*{images[k]}*" if images[k] else "" for k in example_keys]

    def update_credit_from_example(index):
        if index is None:
            return ""
        return credits_list[index[0]]

    examples_component.dataset.click(
        update_credit_from_example,
        inputs=examples_component.dataset,
        outputs=credit_display,
    )

    demo.launch()
