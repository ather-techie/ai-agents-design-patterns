"""Provider-agnostic LLM client with a live and an offline implementation.

Patterns depend only on the :class:`LLMClient` protocol — ``complete(messages,
tools) -> LLMResponse`` — so the exact same pattern code runs against the live
Anthropic API or the deterministic :class:`MockClient`. ``build_client`` reads a
:class:`~shared.config.Config` and returns whichever is appropriate, which is
what lets ``make demo`` / ``make bench`` / tests run with no key and no network.
"""

from __future__ import annotations

from typing import Any, Callable, Protocol, runtime_checkable

from .config import Config
from .errors import ConfigError
from .types import LLMResponse, Message, ToolCall, Usage


@runtime_checkable
class LLMClient(Protocol):
    """The single interface every pattern is written against."""

    model: str

    def complete(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse: ...


class AnthropicClient:
    """Live client wrapping the official ``anthropic`` SDK.

    Uses ``claude-opus-4-8`` with adaptive thinking by default and relies on the
    SDK's built-in retries (429/5xx with backoff). The ``anthropic`` package is
    imported lazily so the framework imports cleanly in mock-only environments
    where the dependency may be absent.
    """

    def __init__(self, config: Config) -> None:
        if not config.api_key:
            raise ConfigError("AnthropicClient requires ANTHROPIC_API_KEY to be set")
        try:
            import anthropic
        except ImportError as exc:  # pragma: no cover - depends on environment
            raise ConfigError(
                "the 'anthropic' package is required for live mode; "
                "install it or run in mock mode (USE_MOCK=1)"
            ) from exc

        self.model = config.model
        self._max_tokens = config.max_tokens
        self._client = anthropic.Anthropic(
            api_key=config.api_key,
            timeout=config.timeout_seconds,
        )

    def complete(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        api_messages = _to_anthropic_messages(messages)
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self._max_tokens,
            "thinking": {"type": "adaptive"},
            "messages": api_messages,
        }
        if tools:
            kwargs["tools"] = tools

        response = self._client.messages.create(**kwargs)
        return _from_anthropic_response(response)


class MockClient:
    """Deterministic offline client driven by a response-planning function.

    The ``planner`` receives the running message list and the available tool
    definitions and returns the next :class:`LLMResponse`. Patterns supply a
    planner that scripts the demo conversation, making demos, tests, and the
    benchmark fully reproducible without a network call.
    """

    def __init__(
        self,
        planner: Callable[[list[Message], list[dict[str, Any]] | None], LLMResponse],
        model: str = "mock",
    ) -> None:
        self.model = model
        self._planner = planner
        self.calls = 0

    def complete(
        self, messages: list[Message], tools: list[dict[str, Any]] | None = None
    ) -> LLMResponse:
        self.calls += 1
        return self._planner(messages, tools)


def build_client(config: Config, *, mock_planner: Callable | None = None) -> LLMClient:
    """Return the right client for ``config``.

    In mock mode a ``mock_planner`` must be supplied (patterns provide their own);
    in live mode an :class:`AnthropicClient` is constructed.
    """
    if config.use_mock:
        if mock_planner is None:
            raise ConfigError("mock mode requires a mock_planner")
        return MockClient(mock_planner, model=f"mock:{config.model}")
    return AnthropicClient(config)


# --- Anthropic <-> framework translation -----------------------------------


def _to_anthropic_messages(messages: list[Message]) -> list[dict[str, Any]]:
    """Convert framework messages to Anthropic Messages API content blocks.

    ``tool`` messages become ``tool_result`` content blocks inside a user turn,
    which is the shape the Messages API expects.
    """
    out: list[dict[str, Any]] = []
    for msg in messages:
        if msg.role == "tool":
            out.append(
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "tool_result",
                            "tool_use_id": msg.tool_call_id,
                            "content": msg.content,
                        }
                    ],
                }
            )
        elif msg.role == "assistant" and msg.tool_calls:
            content: list[dict[str, Any]] = []
            if msg.content:
                content.append({"type": "text", "text": msg.content})
            for call in msg.tool_calls:
                content.append(
                    {
                        "type": "tool_use",
                        "id": call.id,
                        "name": call.name,
                        "input": call.arguments,
                    }
                )
            out.append({"role": "assistant", "content": content})
        else:
            out.append({"role": msg.role, "content": msg.content})
    return out


def _from_anthropic_response(response: Any) -> LLMResponse:
    """Normalize an Anthropic ``Message`` into an :class:`LLMResponse`."""
    text_parts: list[str] = []
    tool_calls: list[ToolCall] = []
    for block in response.content:
        if block.type == "text":
            text_parts.append(block.text)
        elif block.type == "tool_use":
            tool_calls.append(
                ToolCall(id=block.id, name=block.name, arguments=dict(block.input))
            )

    stop_reason = "tool_use" if response.stop_reason == "tool_use" else "end_turn"
    if response.stop_reason == "max_tokens":
        stop_reason = "max_tokens"

    usage = Usage(
        input_tokens=getattr(response.usage, "input_tokens", 0),
        output_tokens=getattr(response.usage, "output_tokens", 0),
    )
    return LLMResponse(
        text="".join(text_parts),
        tool_calls=tool_calls,
        stop_reason=stop_reason,  # type: ignore[arg-type]
        usage=usage,
    )
