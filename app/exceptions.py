"""Custom exceptions for the agent framework."""


class ToolError(Exception):
    """Raised when a tool fails to execute."""

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class TokenLimitExceeded(Exception):
    """Raised when the input token limit would be exceeded."""

    pass
