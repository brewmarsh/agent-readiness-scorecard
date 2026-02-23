import os
from typing import Dict, Any, Optional

try:
    import litellm  # type: ignore
except ImportError:
    litellm = None  # type: ignore


class LLMClient:
    """Provider-Agnostic LLM Client using LiteLLM."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """
        Initializes the LLM client.

        Args:
            config (Dict[str, Any], optional): Configuration dictionary.
                                               Expected keys: "model", "api_key" (optional).
        """
        self.config = config or {}
        # RESOLUTION: Defaulting to gpt-4o for high-fidelity remediation
        self.model = self.config.get("model", "gpt-4o")
        self.api_key = self.config.get("api_key") or os.getenv("LLM_API_KEY")

    def generate(self, system_prompt: str, user_prompt: str) -> str:
        """
        Generates text using the configured LLM.

        Args:
            system_prompt (str): The system instructions.
            user_prompt (str): The user input.

        Returns:
            str: The generated response.

        Raises:
            ImportError: If litellm is not installed.
        """
        if not litellm:
            raise ImportError(
                "litellm is required for LLM features. Please install 'litellm'."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        try:
            # We set temperature to 0 for deterministic code generation
            kwargs = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.0,
            }
            if self.api_key:
                kwargs["api_key"] = self.api_key

            response = litellm.completion(**kwargs)
            return response.choices[0].message.content or ""  # type: ignore
        except Exception as e:
            import sys
            print(f"LLM Generation Error: {e}", file=sys.stderr)
            return ""