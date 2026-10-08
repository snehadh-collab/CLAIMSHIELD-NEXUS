import os
from dotenv import load_dotenv

load_dotenv()

class Settings:
    PROJECT_NAME: str = "CLAIMSHIELD NEXUS"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    
    # Paths
    BASE_DIR: str = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DATA_DIR: str = os.path.join(BASE_DIR, "data")
    CLAIMS_CSV: str = os.path.join(DATA_DIR, "synthetic_claims.csv")
    CLAIMS_JSON: str = os.path.join(DATA_DIR, "synthetic_claims.json")
    POLICIES_MD: str = os.path.join(DATA_DIR, "synthetic_policies.md")
    
    # LLM & AI API Keys
    GEMINI_API_KEY: str = os.environ.get("GEMINI_API_KEY", "")
    GROQ_API_KEY: str = os.environ.get("GROQ_API_KEY", "")
    OLLAMA_BASE_URL: str = os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434")

settings = Settings()
