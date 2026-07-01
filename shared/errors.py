"""Exception hierarchy for the agent framework.

A single base (:class:`AgentError`) lets callers catch everything the framework
raises with one ``except``, while the subclasses carry enough structure for
patterns and tests to branch on specific failure modes.
"""

from __future__ import annotations


class AgentError(Exception):
    """Base class for every error raised by this framework."""


class ConfigError(AgentError):
    """Raised when configuration is missing or invalid."""


class ToolError(AgentError):
    """Raised when a tool fails during execution."""


class ToolValidationError(ToolError):
    """Raised when tool arguments don't satisfy the tool's schema."""


class MaxStepsExceeded(AgentError):
    """Raised when an agent loop hits its step bound without finishing."""

    def __init__(self, max_steps: int) -> None:
        super().__init__(f"agent did not finish within {max_steps} steps")
        self.max_steps = max_steps
