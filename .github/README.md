# Annif-VLM-demo

Developed using Copilot Agent.

This demo is made for a [workshop at Kirjastoverkkopäivät 2025](https://www.kansalliskirjasto.fi/fi/kirjastoverkkopaivat-2025-torstain-tyopajat#tp2-automaattinen-kuvatekstien-tuottaminen-ja-sisallonkuvailu).

## Deploment
Deploy as a Hugging Face Space by just pushing the code to the HF; you can e.g. add HF as a new remote:

    git remote add huggingface git@hf.co:spaces/NatLibFi/Annif-VLM-demo

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

