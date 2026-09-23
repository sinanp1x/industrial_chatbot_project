import os
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

load_dotenv()

def get_openrouter_client(model_name: str = "anthropic/claude-3.5-sonnet", api_key: str = None) -> ChatOpenAI:
    """
    Initializes a ChatOpenAI client configured for OpenRouter.
    """
    if not api_key:
        api_key = os.environ.get("OPENROUTER_API_KEY")
        
    if not api_key:
        raise ValueError("OpenRouter API Key not found. Please set OPENROUTER_API_KEY environment variable or pass it directly.")
        
    return ChatOpenAI(
        model=model_name,
        api_key=api_key,
        base_url="https://openrouter.ai/api/v1",
        default_headers={"HTTP-Referer": "https://roboai.local", "X-Title": "RoboAI Industrial Copilot"}
    )
