class CountryPediaError(Exception):
    """Base exception for all application errors."""
    pass


class NotFoundError(CountryPediaError):
    """Raised when a requested resource is not found."""
    pass


class CountryNotFoundError(NotFoundError):
    """Raised when a country is not found."""
    pass


class UserNotFoundError(NotFoundError):
    """Raised when a user is not found."""
    pass


class AuthenticationError(CountryPediaError):
    """Raised when authentication fails."""
    pass


class TokenExpiredError(AuthenticationError):
    """Raised when a JWT token has expired."""
    pass


class TokenRevokedError(AuthenticationError):
    """Raised when a JWT token has been revoked."""
    pass


class ValidationError(CountryPediaError):
    """Raised when input validation fails."""
    pass


class ExternalAPIError(CountryPediaError):
    """Raised when an external API call fails."""
    pass


class DuplicateEntryError(CountryPediaError):
    """Raised when attempting to create a duplicate entry."""
    pass
