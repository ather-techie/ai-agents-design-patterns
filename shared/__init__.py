"""Shared, provider-agnostic core for the agent design patterns.

This package is the ~50-line-diff foundation the README describes: a normalized
client interface (live + offline mock), a validated tool registry, execution
tracing/visualization, config, errors, and structured logging. Patterns import
from here and stay free of any provider specifics.
"""

from __future__ import annotations

from .config import DEFAULT_MODEL, Config
from .errors import (
    AgentError,
    ConfigError,
    MaxStepsExceeded,
    ToolError,
    ToolValidationError,
)
from .llm_client import AnthropicClient, LLMClient, MockClient, build_client
from .observability import get_logger, log, timed
from .tools import Tool, ToolRegistry
from .trace import Step, Trace, timed_step
from .types import LLMResponse, Message, ToolCall, ToolResult, Usage

__all__ = [
    "DEFAULT_MODEL",
    "Config",
    "AgentError",
    "ConfigError",
    "MaxStepsExceeded",
    "ToolError",
    "ToolValidationError",
    "AnthropicClient",
    "LLMClient",
    "MockClient",
    "build_client",
    "get_logger",
    "log",
    "timed",
    "Tool",
    "ToolRegistry",
    "Step",
    "Trace",
    "timed_step",
    "LLMResponse",
    "Message",
    "ToolCall",
    "ToolResult",
    "Usage",
]
