import os
import sys
import json
from dotenv import load_dotenv
from typing import Dict, List, Optional

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

    def __init__(self, required_keys: List[str]):
        self.required_keys = required_keys
        self.api_keys: Dict[str, str] = {}

        raw = os.getenv("API_KEYS")
        if raw:
            try:
                parsed = json.loads(raw)
                if not isinstance(parsed, dict):
                    raise ValueError("API_KEYS is not a JSON object")
                # keep only string values
                self.api_keys = {k: str(v) for k, v in parsed.items() if v is not None}
                log.info("Loaded API_KEYS from secret", loaded_keys=list(self.api_keys.keys()))
            except Exception as e:
                log.warning("Failed to parse API_KEYS as JSON", error=str(e))

        # Fallback to individual env vars for required keys
        for key in self.required_keys:
            if not self.api_keys.get(key):
                env_val = os.getenv(key)
                if env_val:
                    self.api_keys[key] = env_val
                    log.info("Loaded key from individual env var", key=key)

        # Validate required keys
        missing = [k for k in self.required_keys if not self.api_keys.get(k)]
        if missing:
            log.error("Missing required API keys", missing_keys=missing)
            raise DocumentPortalException(f"Missing API keys: {missing}", sys)

        # Safe log (masked)
        masked = {k: (v[:6] + "...") if v else None for k, v in self.api_keys.items()}
        log.info("API keys ready", keys=masked)

    def get(self, key: str) -> str:
        val = self.api_keys.get(key)
        if not val:
            raise KeyError(f"API key for {key} is missing")
        return val


class ModelLoader:
    """
    - Embeddings: ALWAYS local HuggingFace (NO KEY)
    - LLM: provider-driven via env/config (groq default; huggingface optional)
    """

    def __init__(self):
        env_mode = os.getenv("ENV", "local").lower()
        if env_mode != "production":
            load_dotenv()
            log.info("Running in LOCAL mode: .env loaded", env=env_mode)
        else:
            log.info("Running in PRODUCTION mode", env=env_mode)

        self.config = load_config()
        log.info("YAML config loaded", config_keys=list(self.config.keys()))

        self.provider_key = os.getenv("LLM_PROVIDER", "groq").strip().lower()
        required = self._required_keys_for_provider(self.provider_key)
        self.api_key_mgr = ApiKeyManager(required_keys=required)

    @staticmethod
    def _required_keys_for_provider(provider_key: str) -> List[str]:
        if provider_key == "groq":
            return ["GROQ_API_KEY"]
        if provider_key == "huggingface":
            return ["HUGGINGFACE_API_KEY"]
        # If you add more providers later, map them here.
        return []

    def load_embeddings(self):
        """
        Load local HuggingFace embedding model (FREE, NO KEY).
        You can override via env var EMBEDDING_MODEL_NAME if needed.
        """
        try:
            model_name = os.getenv("EMBEDDING_MODEL_NAME", "sentence-transformers/all-MiniLM-L6-v2")
            log.info("Loading HuggingFace embeddings (local)", model=model_name)
            return HuggingFaceEmbeddings(model_name=model_name)
        except Exception as e:
            log.error("Error loading embedding model", error=str(e))
            raise DocumentPortalException("Failed to load embedding model", sys)

    def load_llm(self):
        """
        Load the configured LLM based on config + LLM_PROVIDER env var.
        Supports:
          - groq (default)
          - huggingface (optional)
        """
        try:
            llm_block = self.config.get("llm", {})
            provider_key = self.provider_key

            if provider_key not in llm_block:
                log.error("LLM provider not found in config", provider=provider_key)
                raise ValueError(f"LLM provider '{provider_key}' not found in config")

            llm_config = llm_block[provider_key]
            provider = (llm_config.get("provider") or provider_key).strip().lower()

            # support both config keys: model / model_name
            model_name = llm_config.get("model") or llm_config.get("model_name")
            if not model_name:
                raise ValueError("Missing model name in config (expected 'model' or 'model_name')")

            temperature = llm_config.get("temperature", 0.2)
            max_tokens = llm_config.get("max_output_tokens", 2048)

            log.info("Loading LLM", provider=provider, model=model_name)

            if provider == "groq":
                return ChatGroq(
                    model=model_name,
                    api_key=self.api_key_mgr.get("GROQ_API_KEY"),
                    temperature=temperature,
                    max_tokens=max_tokens,
                )

            if provider == "huggingface":
                return HuggingFaceEndpoint(
                    repo_id=model_name,
                    huggingfacehub_api_token=self.api_key_mgr.get("HUGGINGFACE_API_KEY"),
                    model_kwargs={"temperature": temperature, "max_new_tokens": max_tokens},
                )

            log.error("Unsupported LLM provider", provider=provider)
            raise ValueError(f"Unsupported LLM provider: {provider}")

        except Exception as e:
            log.error("Error loading LLM", error=str(e))
            raise DocumentPortalException("Failed to load LLM", sys)


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