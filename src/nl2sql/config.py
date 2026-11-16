"""Configuration settings for the NL-to-SQL system."""

import os
from pathlib import Path
from pydantic import BaseModel, Field

# Base paths
ROOT_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = ROOT_DIR / "data"
BENCHMARK_DIR = DATA_DIR / "benchmark_100"
DATABASES_DIR = BENCHMARK_DIR / "databases"
QUESTIONS_FILE = BENCHMARK_DIR / "questions.json"
RESULTS_DIR = ROOT_DIR / "evaluation_results"


class SystemConfig(BaseModel):
    """Runtime configuration for generation, execution, and evaluation."""
    
    # LLM Provider settings: 'ollama', 'gemini', 'openai', 'mock'
    provider: str = Field(default_factory=lambda: os.getenv("NL2SQL_PROVIDER", "ollama"))
    
    # Provider-specific model names
    ollama_model: str = Field(default_factory=lambda: os.getenv("OLLAMA_MODEL", "llama3.2:latest"))
    ollama_host: str = Field(default_factory=lambda: os.getenv("OLLAMA_HOST", "http://localhost:11434"))
    
    openai_api_key: str = Field(default_factory=lambda: os.getenv("OPENAI_API_KEY", ""))
    openai_model: str = Field(default_factory=lambda: os.getenv("OPENAI_MODEL", "gpt-4o-mini"))
    
    gemini_api_key: str = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY", ""))
    gemini_model: str = Field(default_factory=lambda: os.getenv("GEMINI_MODEL", "gemini-1.5-flash"))
    
    # Execution & Self-Correction controls
    max_correction_iterations: int = 3
    query_timeout_seconds: float = 5.0
    max_result_rows: int = 100
    
    # Temperature settings
    temperature: float = 0.0


default_config = SystemConfig()
