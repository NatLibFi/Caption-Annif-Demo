# VLM Caption & Annif Demo

How this works:

1. Upload or take a photo.
2. The image is sent to a Visual Language Model to generate a caption.
3. Annif suggests subjects based on the caption.

Developed using Copilot Agent.

This demo is/was deployed as a Hugging Face Space [NatLibFi/Caption-Annif-Demo](https://huggingface.co/spaces/NatLibFi/Caption-Annif-Demo) for a [workshop at Kirjastoverkkopäivät 2025](https://www.kansalliskirjasto.fi/fi/kirjastoverkkopaivat-2025-torstain-tyopajat#tp2-automaattinen-kuvatekstien-tuottaminen-ja-sisallonkuvailu).

## Deployment
Deploy by just pushing the code to Hugging Face; you can e.g. add HF as a new remote:

    git remote add huggingface git@hf.co:spaces/NatLibFi/Caption-Annif-Demo

and then

    git push huggingface

The app needs these environment variables:
- `ANNIF_API_BASE_URL`
- `VLM_API_KEY`
- `VLM_API_BASE_URL`

For Hugging Face Space deployment they can be set in [repo settings](https://huggingface.co/docs/hub/spaces-overview#managing-secrets).

## Development
When developing you can use autoreload by running the app like this:

    gradio app.py
