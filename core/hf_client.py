import os
import torch
from transformers import AutoModelForCausalLM, AutoTokenizer, pipeline
from langchain_huggingface import ChatHuggingFace, HuggingFacePipeline
from dotenv import load_dotenv

load_dotenv()

def get_hf_client(model_name: str = "mistralai/Mistral-7B-Instruct-v0.2", hf_token: str = None) -> ChatHuggingFace:
    """
    Initializes a ChatHuggingFace client configured for local pipeline execution on Colab.
    Uses 4-bit quantization to fit 7B/8B models in Colab's 16GB T4 GPU.
    """
    if not hf_token:
        hf_token = os.environ.get("HUGGINGFACEHUB_API_TOKEN")
        
    if not hf_token:
        raise ValueError("Hugging Face API Token not found. Please set HUGGINGFACEHUB_API_TOKEN environment variable or pass it directly.")
        
    # Set the token for transformers
    os.environ["HF_TOKEN"] = hf_token
    
    try:
        from transformers import BitsAndBytesConfig
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16
        )
        
        tokenizer = AutoTokenizer.from_pretrained(model_name, token=hf_token)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto",
            token=hf_token
        )
        
        pipe = pipeline(
            "text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
            do_sample=False,
            repetition_penalty=1.03,
            return_full_text=False
        )
        
        llm = HuggingFacePipeline(pipeline=pipe)
        chat_model = ChatHuggingFace(llm=llm)
        return chat_model
        
    except Exception as e:
        raise Exception(f"Failed to load local model {model_name}. Ensure you are running on a GPU with enough VRAM (e.g. Colab T4). Error: {str(e)}")
