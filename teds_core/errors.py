from __future__ import annotations


class TedsError(Exception):
    """Base domain error for user-facing failures."""

    pass


class SchemaResolutionError(TedsError):
    """Error resolving schema references or loading schema files."""

    pass


class ValidationError(TedsError):
    """Error during test case validation."""

    pass


class NetworkError(TedsError):
    """Error during network operations."""

    pass


class ConfigurationError(TedsError):
    """Error in configuration or input parameters."""

    pass


class TemplateError(TedsError):
    """Error in template processing."""

    pass
