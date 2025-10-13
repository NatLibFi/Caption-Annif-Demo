import gradio as gr
import requests
from annif_client import AnnifClient
import os


# Get VLM API base URL and API key from environment variables
VLM_API_BASE_URL = os.getenv("VLM_API_BASE_URL")
if not VLM_API_BASE_URL:
    raise RuntimeError("VLM_API_BASE_URL environment variable must be set.")
VLM_API_KEY = os.getenv("VLM_API_KEY", "")
VLM_API_ENDPOINT = f"{VLM_API_BASE_URL}/v1/chat/completions"


# Initialize Annif client (no arguments)
annif = AnnifClient()


def get_caption(image):
    # Convert image to base64 JPEG
    import io
    import base64

    buf = io.BytesIO()
    image.save(buf, format="JPEG")
    img_bytes = buf.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode("utf-8")

    # Prepare payload for VLM (OpenAI schema)
    payload = {
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": "What is in this image?"},
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


PROJECT_ID = "yso-en"  # Placeholder, update as needed


def get_subjects(caption):
    try:
        results = annif.suggest(project_id=PROJECT_ID, text=caption)
        label_scores = {result["label"]: result["score"] for result in results}
        if not label_scores:
            return {}
        return label_scores
    except Exception as e:
        print(f"Annif API error: {e}")  # Detailed error for admin
        raise gr.Error("Sorry, there was a problem getting subject suggestions.")


def process_image(image):
    caption = get_caption(image)
    subjects = get_subjects(caption)
    return image, caption, subjects


demo = gr.Interface(
    fn=lambda image: process_image(image)[1:],  # Only return caption and subjects
    inputs=gr.Image(type="pil", label="Upload or take a photo"),
    outputs=[
        gr.Textbox(label="Caption"),
        gr.Label(label="Subject Suggestions", show_heading=False),
    ],
    title="VLM Caption & Annif Subject Demo",
    description="Upload or take a photo. The app generates a caption using a Visual Language Model and suggests subjects using Annif.",
)

demo.launch()
