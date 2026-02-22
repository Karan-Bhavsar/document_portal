import os
import sys
import json
from dotenv import load_dotenv

# Ensure project root is in PYTHONPATH
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.config_loader import load_config
from langchain_huggingface import HuggingFaceEmbeddings

from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEndpoint

from logger.custom_logger import CustomLogger
from exception.custom_exception import DocumentPortalException

log = CustomLogger().get_logger(__name__)


class ApiKeyManager:
    REQUIRED_KEYS = ["GROQ_API_KEY"]

    def __init__(self):
        self.api_keys = {}
        raw = os.getenv("API_KEYS")

        if raw:
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise ValueError("API_KEYS is not a valid JSON object")
                self.api_keys = parsed
                log.info("Loaded API_KEYS from ECS secret")
            except Exception as e:
                log.warning("Failed to parse API_KEYS as JSON", error=str(e))

        # Fallback to individual env vars
        for key in self.REQUIRED_KEYS:
            if not self.api_keys.get(key):
                env_val = os.getenv(key)
                if env_val:
                    self.api_keys[key] = env_val
                    log.info(f"Loaded {key} from individual env var")

        # Final check
        missing = [k for k in self.REQUIRED_KEYS if not self.api_keys.get(k)]
        if missing:
            log.error("Missing required API keys", missing_keys=missing)
            raise DocumentPortalException("Missing API keys", sys)

        log.info("API keys loaded", keys={k: v[:6] + "..." for k, v in self.api_keys.items()})


    def get(self, key: str) -> str:
        val = self.api_keys.get(key)
        if not val:
            raise KeyError(f"API key for {key} is missing")
        return val
    
class ModelLoader:
    """
    Loads embedding models and LLMs based on config and environment.
    """

    def __init__(self):
        if os.getenv("ENV", "local").lower() != "production":
            load_dotenv()
            log.info("Running in LOCAL mode: .env loaded")
        else:
            log.info("Running in PRODUCTION mode")

        self.api_key_mgr = ApiKeyManager()
        self.config = load_config()
        log.info("YAML config loaded", config_keys=list(self.config.keys()))
        
    def validate_env(self):
        """
        Validate required env vars based on provider.
        """
        provider_key = os.getenv("LLM_PROVIDER", "groq").lower()

        if provider_key == "groq":
            if not os.getenv("GROQ_API_KEY"):
                raise DocumentPortalException("Missing GROQ_API_KEY in .env", sys)

        elif provider_key == "huggingface":
            if not os.getenv("HUGGINGFACE_API_KEY"):
                raise DocumentPortalException("Missing HUGGINGFACE_API_KEY in .env", sys)

        # embeddings (HF local) need no key

    def load_embeddings(self):
        """
        Load local HuggingFace embedding model (FREE).
        """
        try:
            model_name = "sentence-transformers/all-MiniLM-L6-v2"
            log.info("Loading HuggingFace embedding model", model=model_name)
            return HuggingFaceEmbeddings(model_name=model_name)
        except Exception as e:
            log.error("Error loading embedding model", error=str(e))
            raise DocumentPortalException("Failed to load embedding model", sys)

    def load_llm(self):
    
        llm_block = self.config["llm"]
        provider_key = os.getenv("LLM_PROVIDER", "groq")  # default = groq

        if provider_key not in llm_block:
            log.error("LLM provider not found in config", provider=provider_key)
            raise ValueError(f"LLM provider '{provider_key}' not found in config")

        llm_config = llm_block[provider_key]
        provider = llm_config.get("provider")

        # ✅ support both keys: model / model_name
        model_name = llm_config.get("model") or llm_config.get("model_name")
        if not model_name:
            raise ValueError("Missing model name in config (expected 'model' or 'model_name')")

        temperature = llm_config.get("temperature", 0.2)
        max_tokens = llm_config.get("max_output_tokens", 2048)

        log.info("Loading LLM", provider=provider, model=model_name)

        if provider == "groq":
            return ChatGroq(
                model=model_name,
                api_key=os.getenv("GROQ_API_KEY"),
                temperature=temperature,
                max_tokens=max_tokens
            )

        elif provider == "huggingface":
            return HuggingFaceEndpoint(
                repo_id=model_name,
                huggingfacehub_api_token=os.getenv("HUGGINGFACE_API_KEY"),
                model_kwargs={"temperature": temperature, "max_new_tokens": max_tokens}
            )

        else:
            log.error("Unsupported LLM provider", provider=provider)
            raise ValueError(f"Unsupported LLM provider: {provider}")



if __name__ == "__main__":
    loader = ModelLoader()

    # Test embeddings
    print("\nTesting Embeddings...")
    emb = loader.load_embeddings()
    vector = emb.embed_query("hello world")
    print("Embedding size:", len(vector))

    # Test LLM
    print("\nTesting LLM...")
    llm = loader.load_llm()
    response = llm.invoke("Say hello in one short sentence.")
    print("LLM response:", response.content)

