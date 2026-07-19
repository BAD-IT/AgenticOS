import os
from litellm import completion

def test_ollama_local_llm():
    """Verifies that LiteLLM can connect to the local Ollama gemma4:12b model."""
    model = os.getenv("LLM_MODEL", "ollama/gemma4:12b")
    api_base = os.getenv("OLLAMA_API_BASE", "http://localhost:11434")
    
    response = completion(
        model=model,
        messages=[{"role": "user", "content": "Hello, say strictly 'Pong'"}],
        api_base=api_base
    )
    
    content = response.choices[0].message.content
    assert content is not None
    assert "pong" in content.lower()
