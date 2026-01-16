"""Custom exception classes for Lucid backend."""


class LucidError(Exception):
    """Base exception for all Lucid errors."""
    pass


class IngestionError(LucidError):
    """Error during data ingestion."""
    pass


class AnalyticsError(LucidError):
    """Error during analytics computation."""
    pass


class InsightError(LucidError):
    """Error during insight generation."""
    pass


class AIServiceError(LucidError):
    """Error with AI service."""
    pass


class CacheError(LucidError):
    """Error with cache operations."""
    pass


class DatabaseError(LucidError):
    """Error with database operations."""
    pass


class ValidationError(LucidError):
    """Data validation error."""
    pass
