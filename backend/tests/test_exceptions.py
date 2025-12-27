"""
Comprehensive test suite for exceptions module

Tests cover:
- Custom exception hierarchy
- Exception inheritance chain
- Exception message handling
- Exception raising and catching
- Type checking and isinstance behavior
"""
import pytest
from exceptions import (
    GameServiceError,
    GameNotFoundError,
    BGGServiceError,
    ValidationError,
    DatabaseError,
)


class TestExceptionHierarchy:
    """Test exception inheritance and hierarchy"""

    def test_game_service_error_is_exception(self):
        """Test GameServiceError inherits from Exception"""
        exc = GameServiceError("Test error")
        assert isinstance(exc, Exception)
        assert isinstance(exc, GameServiceError)

    def test_game_not_found_error_hierarchy(self):
        """Test GameNotFoundError inherits from GameServiceError"""
        exc = GameNotFoundError("Game not found")
        assert isinstance(exc, Exception)
        assert isinstance(exc, GameServiceError)
        assert isinstance(exc, GameNotFoundError)

    def test_bgg_service_error_hierarchy(self):
        """Test BGGServiceError inherits from GameServiceError"""
        exc = BGGServiceError("BGG API failed")
        assert isinstance(exc, Exception)
        assert isinstance(exc, GameServiceError)
        assert isinstance(exc, BGGServiceError)

    def test_validation_error_hierarchy(self):
        """Test ValidationError inherits from GameServiceError"""
        exc = ValidationError("Validation failed")
        assert isinstance(exc, Exception)
        assert isinstance(exc, GameServiceError)
        assert isinstance(exc, ValidationError)

    def test_database_error_hierarchy(self):
        """Test DatabaseError inherits from GameServiceError"""
        exc = DatabaseError("Database operation failed")
        assert isinstance(exc, Exception)
        assert isinstance(exc, GameServiceError)
        assert isinstance(exc, DatabaseError)


class TestExceptionMessages:
    """Test exception message handling"""

    def test_game_service_error_message(self):
        """Test GameServiceError stores message correctly"""
        message = "Test error message"
        exc = GameServiceError(message)
        assert str(exc) == message

    def test_game_not_found_error_message(self):
        """Test GameNotFoundError stores message correctly"""
        message = "Game with ID 123 not found"
        exc = GameNotFoundError(message)
        assert str(exc) == message

    def test_bgg_service_error_message(self):
        """Test BGGServiceError stores message correctly"""
        message = "BGG API returned 404"
        exc = BGGServiceError(message)
        assert str(exc) == message

    def test_validation_error_message(self):
        """Test ValidationError stores message correctly"""
        message = "Invalid BGG ID provided"
        exc = ValidationError(message)
        assert str(exc) == message

    def test_database_error_message(self):
        """Test DatabaseError stores message correctly"""
        message = "Connection to database failed"
        exc = DatabaseError(message)
        assert str(exc) == message

    def test_exception_with_empty_message(self):
        """Test exceptions can be created with empty message"""
        exc = GameServiceError("")
        assert str(exc) == ""

    def test_exception_with_no_args(self):
        """Test exceptions can be created without arguments"""
        exc = GameServiceError()
        assert str(exc) == ""


class TestExceptionRaising:
    """Test raising and catching exceptions"""

    def test_raise_game_service_error(self):
        """Test raising GameServiceError"""
        with pytest.raises(GameServiceError) as exc_info:
            raise GameServiceError("Test error")

        assert "Test error" in str(exc_info.value)

    def test_raise_game_not_found_error(self):
        """Test raising GameNotFoundError"""
        with pytest.raises(GameNotFoundError) as exc_info:
            raise GameNotFoundError("Game not found")

        assert "Game not found" in str(exc_info.value)

    def test_raise_bgg_service_error(self):
        """Test raising BGGServiceError"""
        with pytest.raises(BGGServiceError) as exc_info:
            raise BGGServiceError("BGG API failed")

        assert "BGG API failed" in str(exc_info.value)

    def test_raise_validation_error(self):
        """Test raising ValidationError"""
        with pytest.raises(ValidationError) as exc_info:
            raise ValidationError("Invalid input")

        assert "Invalid input" in str(exc_info.value)

    def test_raise_database_error(self):
        """Test raising DatabaseError"""
        with pytest.raises(DatabaseError) as exc_info:
            raise DatabaseError("DB connection failed")

        assert "DB connection failed" in str(exc_info.value)


class TestExceptionCatching:
    """Test catching exceptions at different hierarchy levels"""

    def test_catch_game_not_found_as_game_service_error(self):
        """Test GameNotFoundError can be caught as GameServiceError"""
        with pytest.raises(GameServiceError):
            raise GameNotFoundError("Not found")

    def test_catch_bgg_service_error_as_game_service_error(self):
        """Test BGGServiceError can be caught as GameServiceError"""
        with pytest.raises(GameServiceError):
            raise BGGServiceError("BGG failed")

    def test_catch_validation_error_as_game_service_error(self):
        """Test ValidationError can be caught as GameServiceError"""
        with pytest.raises(GameServiceError):
            raise ValidationError("Validation failed")

    def test_catch_database_error_as_game_service_error(self):
        """Test DatabaseError can be caught as GameServiceError"""
        with pytest.raises(GameServiceError):
            raise DatabaseError("DB failed")

    def test_catch_all_as_exception(self):
        """Test all custom exceptions can be caught as Exception"""
        exceptions = [
            GameServiceError("Test"),
            GameNotFoundError("Test"),
            BGGServiceError("Test"),
            ValidationError("Test"),
            DatabaseError("Test"),
        ]

        for exc in exceptions:
            with pytest.raises(Exception):
                raise exc

    def test_specific_exception_not_caught_by_sibling(self):
        """Test specific exceptions are not caught by sibling exceptions"""
        # GameNotFoundError should not be caught as BGGServiceError
        with pytest.raises(GameNotFoundError):
            try:
                raise GameNotFoundError("Not found")
            except BGGServiceError:
                pytest.fail("Should not catch GameNotFoundError as BGGServiceError")


class TestExceptionTypeChecking:
    """Test type checking and isinstance behavior"""

    def test_isinstance_checks(self):
        """Test isinstance checks for exception hierarchy"""
        exc = GameNotFoundError("Test")

        assert isinstance(exc, GameNotFoundError)
        assert isinstance(exc, GameServiceError)
        assert isinstance(exc, Exception)
        assert not isinstance(exc, BGGServiceError)
        assert not isinstance(exc, ValidationError)
        assert not isinstance(exc, DatabaseError)

    def test_type_equality(self):
        """Test type equality checks"""
        exc = GameServiceError("Test")

        assert type(exc) == GameServiceError
        assert type(exc) != Exception
        assert type(exc) != GameNotFoundError

    def test_exception_comparison(self):
        """Test exceptions with same message are not equal"""
        exc1 = GameServiceError("Test")
        exc2 = GameServiceError("Test")

        # Different exception instances should not be equal
        assert exc1 != exc2


class TestExceptionUsagePatterns:
    """Test common usage patterns for exceptions"""

    def test_exception_in_function(self):
        """Test raising exception from function"""
        def find_game(game_id):
            if game_id <= 0:
                raise ValidationError("Game ID must be positive")
            if game_id == 999:
                raise GameNotFoundError(f"Game {game_id} not found")
            return {"id": game_id, "title": "Test Game"}

        # Valid game ID
        result = find_game(1)
        assert result["id"] == 1

        # Invalid game ID (validation error)
        with pytest.raises(ValidationError) as exc_info:
            find_game(-1)
        assert "positive" in str(exc_info.value)

        # Non-existent game (not found error)
        with pytest.raises(GameNotFoundError) as exc_info:
            find_game(999)
        assert "999" in str(exc_info.value)

    def test_exception_chain(self):
        """Test exception chaining with 'from' syntax"""
        def outer_function():
            try:
                inner_function()
            except BGGServiceError as e:
                raise DatabaseError("Failed to save BGG data") from e

        def inner_function():
            raise BGGServiceError("BGG API timeout")

        with pytest.raises(DatabaseError) as exc_info:
            outer_function()

        # Check the cause is preserved
        assert exc_info.value.__cause__ is not None
        assert isinstance(exc_info.value.__cause__, BGGServiceError)

    def test_exception_with_multiple_handlers(self):
        """Test multiple exception handlers in order"""
        def process_game(game_id):
            if game_id < 0:
                raise ValidationError("Invalid ID")
            elif game_id == 0:
                raise GameNotFoundError("No game with ID 0")
            elif game_id == 999:
                raise BGGServiceError("BGG unavailable")
            return "success"

        # Test ValidationError handler
        try:
            process_game(-1)
            pytest.fail("Should raise ValidationError")
        except ValidationError as e:
            assert "Invalid" in str(e)
        except GameServiceError:
            pytest.fail("Should catch ValidationError specifically")

        # Test GameNotFoundError handler
        try:
            process_game(0)
            pytest.fail("Should raise GameNotFoundError")
        except GameNotFoundError as e:
            assert "No game" in str(e)
        except GameServiceError:
            pytest.fail("Should catch GameNotFoundError specifically")

        # Test catching any GameServiceError
        try:
            process_game(999)
            pytest.fail("Should raise BGGServiceError")
        except GameServiceError as e:
            assert isinstance(e, BGGServiceError)


class TestExceptionRepr:
    """Test exception string representations"""

    def test_exception_repr(self):
        """Test exception repr includes class name and message"""
        exc = GameNotFoundError("Game 123 not found")
        repr_str = repr(exc)

        assert "GameNotFoundError" in repr_str
        assert "Game 123 not found" in repr_str

    def test_exception_str(self):
        """Test exception str returns just the message"""
        message = "Test error message"
        exc = GameServiceError(message)

        assert str(exc) == message
