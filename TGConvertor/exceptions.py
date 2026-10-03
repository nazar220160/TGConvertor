"""Public errors raised by TGConvertor."""


class ValidationError(ValueError):
    """A session is malformed, incomplete, or cannot represent the target format."""


class MissingDependencyError(ImportError):
    """An optional client or tdata dependency is not installed."""
