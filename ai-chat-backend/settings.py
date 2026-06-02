import os

DATABASE_URL = os.environ["DATABASE_URL"]
HF_TOKEN = os.environ["HF_TOKEN"]
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
OPENROUTER_DEFAULT_MODEL = os.getenv(
    "OPENROUTER_DEFAULT_MODEL",
    "deepseek/deepseek-chat-v3-0324:free",
)
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_DEFAULT_MODEL = os.getenv("GEMINI_DEFAULT_MODEL", "gemini-2.5-flash")

CORS_ORIGINS = ["https://ai-chat-platform.netlify.app"]

MODEL_NAME = "meta-llama/Llama-3.1-8B-Instruct"
MAX_TOKENS = 600
TEMPERATURE = 0.6
HISTORY_LIMIT = 12

SYSTEM_PROMPT = (
    "Eres el asistente oficial de AI Chat Platform y este chat usa Hugging Face. "
    "Responde en el mismo idioma del usuario, de forma breve, clara y util. "
    "Solo cuando te pregunten explicitamente por tu identidad o proveedor, "
    "aclara que eres el asistente de AI Chat Platform y que usas Hugging Face."
)
