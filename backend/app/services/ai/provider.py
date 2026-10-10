from collections.abc import Mapping, Sequence
from typing import Protocol, TypeAlias, runtime_checkable

ChatMessage: TypeAlias = Mapping[str, str]
ProviderOptions: TypeAlias = Mapping[str, str | int | float | bool | None]


@runtime_checkable
class AIProvider(Protocol):
    """Provider-neutral contract for optional text generation and embeddings.

    Implementations must honor configured timeouts and avoid transmitting customer
    identifiers or other personal information. Callers must handle provider errors
    and fall back to deterministic rule-based behavior.
    """

    async def complete(
        self,
        messages: Sequence[ChatMessage],
        *,
        options: ProviderOptions | None = None,
    ) -> str:
        """Return generated text for a sequence of role/content messages."""
        ...

    async def embed(
        self,
        texts: Sequence[str],
        *,
        options: ProviderOptions | None = None,
    ) -> list[list[float]]:
        """Return one embedding vector for each input text."""
        ...
