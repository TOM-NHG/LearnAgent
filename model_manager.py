"""
Dynamic Multi-Model Manager for MRP AI Agent.
Supports seamless switching between:
- Local Ollama: qwen2.5:1.5b (Fast CPU 1-3s), qwen2.5:7b-instruct (Deep local CPU)
- Cloud LLMs: Groq (llama-3.3-70b-versatile, ~400ms free tier), OpenAI (gpt-4o-mini)
Tracks latency and performance statistics for real-time benchmarking.
"""
import os
import time
from typing import Dict, Any, Optional
from langchain_openai import ChatOpenAI
from dotenv import load_dotenv

PROJECT_ROOT = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

class ModelManager:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ModelManager, cls).__new__(cls)
            cls._instance._init_manager()
        return cls._instance

    def _init_manager(self):
        # Default state
        self.provider = os.getenv("LLM_PROVIDER", "ollama").lower()
        self.model = os.getenv("OLLAMA_MODEL", "qwen2.5:1.5b")  # default to fast 1.5b
        self.api_key = os.getenv("OPENAI_API_KEY", "")
        self.groq_api_key = os.getenv("GROQ_API_KEY", "")
        self.fast_path_enabled = True  # Can be toggled on/off
        self.performance_history = []
        self._llm_instance = None
        self._rebuild_llm()

    def _rebuild_llm(self):
        """Constructs LangChain ChatOpenAI client based on provider."""
        try:
            if self.provider == "groq":
                key = self.groq_api_key or self.api_key
                self._llm_instance = ChatOpenAI(
                    base_url="https://api.groq.com/openai/v1",
                    api_key=key if key else "dummy",
                    model=self.model if self.model else "llama-3.3-70b-versatile",
                    temperature=0
                )
            elif self.provider == "openai":
                self._llm_instance = ChatOpenAI(
                    model=self.model if self.model else "gpt-4o-mini",
                    temperature=0,
                    api_key=self.api_key if self.api_key else "dummy"
                )
            else: # ollama
                self.provider = "ollama"
                self._llm_instance = ChatOpenAI(
                    base_url="http://localhost:11434/v1",
                    api_key="ollama",
                    model=self.model if self.model else "qwen2.5:1.5b",
                    temperature=0
                )
        except Exception as e:
            print(f"⚠️ Error building LLM client ({self.provider}:{self.model}): {e}")
            self._llm_instance = None

    def get_llm(self):
        if self._llm_instance is None:
            self._rebuild_llm()
        return self._llm_instance

    def update_config(self, provider: str, model: str, api_key: Optional[str] = None, fast_path_enabled: Optional[bool] = None) -> Dict[str, Any]:
        """Update runtime model configuration without restarting server."""
        self.provider = provider.lower()
        self.model = model
        if api_key is not None:
            if self.provider == "groq":
                self.groq_api_key = api_key
            else:
                self.api_key = api_key

        if fast_path_enabled is not None:
            self.fast_path_enabled = fast_path_enabled

        self._rebuild_llm()
        return self.get_status()

    def get_status(self) -> Dict[str, Any]:
        has_key = bool(self.groq_api_key) if self.provider == "groq" else bool(self.api_key and self.api_key != "your_openai_api_key_here")
        return {
            "provider": self.provider,
            "model": self.model,
            "has_api_key": has_key,
            "fast_path_enabled": self.fast_path_enabled,
            "available_models": {
                "ollama": ["qwen2.5:1.5b", "qwen2.5:7b-instruct"],
                "groq": ["llama-3.3-70b-versatile", "qwen-2.5-32b", "llama-3.1-8b-instant"],
                "openai": ["gpt-4o-mini", "gpt-4o"]
            },
            "recent_metrics": self.performance_history[-6:]
        }

    def record_metric(self, question: str, source: str, total_time_ms: float, cypher_time_ms: Optional[float] = None, cypher: Optional[str] = None):
        metric = {
            "timestamp": time.time(),
            "question": question[:45] + "..." if len(question) > 45 else question,
            "provider": self.provider if "LLM" in source else "System",
            "model": self.model if "LLM" in source else "Regex/SQL",
            "source": source,
            "total_time_ms": round(total_time_ms, 2),
            "cypher_time_ms": round(cypher_time_ms, 2) if cypher_time_ms else 0,
            "has_cypher": bool(cypher)
        }
        self.performance_history.append(metric)
        if len(self.performance_history) > 50:
            self.performance_history.pop(0)

model_manager = ModelManager()
