from collections.abc import Sequence

from app.services.ai.provider import AIProvider, ChatMessage, ProviderOptions


class FakeAIProvider:
    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        options: ProviderOptions | None = None,
    ) -> str:
        return str(messages[0]["content"]) if messages else ""

    async def embed(
        self,
        texts: Sequence[str],
        *,
        options: ProviderOptions | None = None,
    ) -> list[list[float]]:
        return [[float(len(text))] for text in texts]


def test_ai_provider_protocol_supports_complete_and_embed() -> None:
    provider = FakeAIProvider()
    assert isinstance(provider, AIProvider)
