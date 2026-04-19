from __future__ import annotations

import os
from typing import Any, Dict, List, Optional, Union

try:
    from crewai import BaseLLM
except ImportError:  # pragma: no cover - compatibility fallback
    from crewai.llms.base_llm import BaseLLM
from backend.config import settings


class OCIGenAIConfigFileLLM(BaseLLM):
    """CrewAI custom LLM backed by OCI GenAI SDK request signing."""

    def __init__(
        self,
        model: str,
        compartment_id: str,
        endpoint: str,
        config_file: str = "~/.oci/config",
        config_profile: str = "",
        temperature: Optional[float] = 0.2,
        max_tokens: int = 4096,
    ) -> None:
        super().__init__(model=model, temperature=temperature)
        self.compartment_id = compartment_id
        self.endpoint = endpoint
        self.config_file = os.path.expanduser(config_file)
        self.config_profile = config_profile
        self.max_tokens = max_tokens
        self.client = self._build_client()

    def _build_client(self):
        import oci

        oci_config = oci.config.from_file(self.config_file, self.config_profile)

        # Keep existing env/config override behavior for region when provided.
        if settings.oci_region:
            oci_config["region"] = settings.oci_region

        endpoint = self.endpoint.rstrip("/")
        if endpoint.endswith("/20231130"):
            endpoint = endpoint.rsplit("/20231130", 1)[0]

        return oci.generative_ai_inference.GenerativeAiInferenceClient(
            oci_config,
            service_endpoint=endpoint,
        )

    @staticmethod
    def _to_prompt(messages: Union[str, List[Dict[str, str]]]) -> str:
        if isinstance(messages, str):
            return messages
        lines = []
        for msg in messages:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if content:
                lines.append(f"{role}: {content}")
        return "\n".join(lines)

    def _generate_text_response(self, prompt: str) -> str:
        import oci

        inference_request = oci.generative_ai_inference.models.CohereLlmInferenceRequest(
            prompt=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature if self.temperature is not None else 0.2,
        )
        response = self.client.generate_text(
            oci.generative_ai_inference.models.GenerateTextDetails(
                compartment_id=self.compartment_id,
                serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                    model_id=self.model
                ),
                inference_request=inference_request,
            )
        )
        generated = getattr(response.data.inference_response, "generated_texts", None)
        if not generated:
            raise RuntimeError("OCI GenAI returned an empty text-generation response")
        return getattr(generated[0], "text", "")

    def _generate_chat_response(self, prompt: str) -> str:
        import oci

        chat_request = oci.generative_ai_inference.models.CohereChatRequest(
            message=prompt,
            max_tokens=self.max_tokens,
            temperature=self.temperature if self.temperature is not None else 0.2,
            stop_sequences=self.stop if self.stop else None,
        )
        response = self.client.chat(
            oci.generative_ai_inference.models.ChatDetails(
                compartment_id=self.compartment_id,
                serving_mode=oci.generative_ai_inference.models.OnDemandServingMode(
                    model_id=self.model
                ),
                chat_request=chat_request,
            )
        )
        chat_response = getattr(response.data, "chat_response", None)
        text = getattr(chat_response, "text", "") if chat_response else ""
        if not text:
            raise RuntimeError("OCI GenAI returned an empty chat response")
        return text

    def chat(
        self,
        message: str,
        history: Optional[List[Dict[str, str]]] = None,
        system_prompt: Optional[str] = None,
    ) -> str:
        """
        Convenience helper for direct conversational calls to OCI chat inference.
        History is inlined into a single chat message to keep SDK usage stable
        across model versions and avoid strict schema coupling.
        """
        history_lines: list[str] = []
        if system_prompt:
            history_lines.append(f"system: {system_prompt}")
        if history:
            for item in history:
                role = item.get("role", "user")
                content = item.get("content", "")
                if content:
                    history_lines.append(f"{role}: {content}")
        history_lines.append(f"user: {message}")
        prompt = "\n".join(history_lines)
        return self._generate_chat_response(prompt)

    def call(
        self,
        messages: Union[str, List[Dict[str, str]]],
        tools: Optional[List[dict]] = None,
        callbacks: Optional[List[Any]] = None,
        available_functions: Optional[Dict[str, Any]] = None,
        from_task: Any = None,
        from_agent: Any = None,
        response_model: Any = None,
        **kwargs: Any,
    ) -> str:
        import oci

        prompt = self._to_prompt(messages)
        try:
            text = self._generate_chat_response(prompt)
        except oci.exceptions.ServiceError as exc:
            # Fallback for models/endpoints that expose generateText instead of chat.
            if "does not support Chat" in str(exc):
                text = self._generate_text_response(prompt)
            else:
                raise
        if self.stop:
            for stop_word in self.stop:
                if stop_word in text:
                    text = text.split(stop_word, 1)[0]
                    break
        return text

    def supports_function_calling(self) -> bool:
        return False

    def supports_stop_words(self) -> bool:
        return False

    def get_context_window_size(self) -> int:
        return 128000


def get_oci_llm() -> BaseLLM:
    """
    OCI GenAI LLM for CrewAI using OCI SDK request-signing auth.
    Reads credentials from OCI config file (~/.oci/config by default).
    """
    if not settings.oci_compartment_id:
        raise ValueError("OCI_COMPARTMENT_ID is required for OCI GenAI inference")
    if not settings.oci_config_profile:
        raise ValueError("OCI_CONFIG_PROFILE is required (do not rely on DEFAULT)")

    return OCIGenAIConfigFileLLM(
        model=settings.oci_genai_model_id,
        compartment_id=settings.oci_compartment_id,
        endpoint=settings.oci_genai_endpoint,
        config_file=settings.oci_config_file,
        config_profile=settings.oci_config_profile,
        temperature=0.2,
        max_tokens=4096,
    )


def chat_with_oci(
    message: str,
    history: Optional[List[Dict[str, str]]] = None,
    system_prompt: Optional[str] = None,
) -> str:
    """
    Direct OCI chat inference helper used by chat-session APIs.
    """
    llm = get_oci_llm()
    if not isinstance(llm, OCIGenAIConfigFileLLM):
        # Defensive fallback for alternate BaseLLM implementations.
        prompt = "\n".join(
            [*(f"{m.get('role', 'user')}: {m.get('content', '')}" for m in (history or [])), message]
        )
        return llm.call(prompt)
    return llm.chat(message=message, history=history, system_prompt=system_prompt)


def get_embedding_fn():
    """
    Returns a callable that generates embeddings using the in-database
    ONNX model loaded into ADB 26ai. No external API call needed.
    Used for query-side embedding during semantic search.
    """
    import oracledb
    from backend.db.connection import get_connection

    def embed_text(text: str) -> list:
        conn = get_connection()
        cursor = conn.cursor()
        cursor.execute(
            """
            SELECT TO_VECTOR(DBMS_VECTOR.UTL_TO_EMBEDDING(
                :text_input,
                JSON('{"provider":"database","model":"ALL_MINILM_L12_V2"}')
            )) FROM DUAL
            """,
            {"text_input": text},
        )
        row = cursor.fetchone()
        cursor.close()
        return row[0] if row else []

    return embed_text
