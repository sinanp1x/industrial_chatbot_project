import os
from huggingface_hub import snapshot_download

MODEL_NAME = "mistralai/Mistral-7B-Instruct-v0.2"

if __name__ == "__main__":
    # Optional: get HF token from env for gated models; public models don't need it
    hf_token = os.getenv("HUGGINGFACEHUB_API_TOKEN")
    print(f"Downloading model {MODEL_NAME}... This may take a few minutes.")
    snapshot_download(repo_id=MODEL_NAME, token=hf_token, local_dir="models", local_dir_use_symlinks=False)
    print("Model download complete. The files are stored under ./models.")
