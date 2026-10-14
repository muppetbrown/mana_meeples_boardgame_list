from config import normalize_database_url


def test_bare_postgresql_url_pins_psycopg2():
    assert normalize_database_url("postgresql://u:p@h:5432/db") == "postgresql+psycopg2://u:p@h:5432/db"


def test_legacy_postgres_scheme_is_rewritten():
    assert normalize_database_url("postgres://u:p@h/db") == "postgresql+psycopg2://u:p@h/db"


def test_explicit_driver_and_other_urls_untouched():
    assert normalize_database_url("postgresql+psycopg2://u@h/db") == "postgresql+psycopg2://u@h/db"
    assert normalize_database_url("sqlite:///./app.db") == "sqlite:///./app.db"
    assert normalize_database_url("") == ""
