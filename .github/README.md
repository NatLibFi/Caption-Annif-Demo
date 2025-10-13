# Annif-VML-demo

Developed using Copilot Agent.

Deploy as a Hugging Face Space by just pushing the code to the HF; you can e.g. add HF as a new remote:

    git remote add huggingface git@hf.co:spaces/NatLibFi/Annif-VLM-demo

The app needs these environment variables:
- `ANNIF_API_BASE_URL`
- `VLM_API_KEY`
- `VLM_API_BASE_URL`

When developing you can use autoreload by running the app like this:

    gradio app.py

