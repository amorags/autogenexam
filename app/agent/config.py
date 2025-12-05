LLM_CONFIG = {
    "config_list": [
        {
            "model": "llama3.1",
            "api_type": "ollama",
            "api_base": "http://localhost:11434",
            "api_rate_limit": 0.25,
            "temperature": 0.0,
            "repeat_penalty": 1.1,
            "seed": 42,
            "stream": False,
            "native_tool_calls": True,
            "cache_seed": None,
        }
    ]
}