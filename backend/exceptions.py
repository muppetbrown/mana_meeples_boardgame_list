"""Custom exception hierarchy for the application"""


class GameServiceError(Exception):
    """Base exception for game service operations"""

    pass


class GameNotFoundError(GameServiceError):
    """Raised when a requested game is not found"""

    pass


class BGGServiceError(GameServiceError):
    """Raised when BGG service operations fail"""

    pass


class ValidationError(GameServiceError):
    """Raised when input validation fails"""

    pass


class DatabaseError(GameServiceError):
    """Raised when database operations fail"""

    pass
