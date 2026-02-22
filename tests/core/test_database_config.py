import pytest
from unittest.mock import patch
from src.database.config import get_tortoise_config

def test_get_tortoise_config_sqlite():
    with patch('src.database.config.Settings') as MockSettings:
        mock_settings = MockSettings.return_value
        mock_settings.POSTGRES_HOST = None
        mock_settings.DATABASE_PATH = "data/test.db"
        
        config = get_tortoise_config()
        
        assert config["connections"]["default"] == "sqlite://data/test.db"
        assert config["apps"]["models"]["models"] == ["src.database.models", "aerich.models"]
        assert config["apps"]["models"]["default_connection"] == "default"

def test_get_tortoise_config_postgres():
    with patch('src.database.config.Settings') as MockSettings:
        mock_settings = MockSettings.return_value
        mock_settings.POSTGRES_HOST = "localhost"
        mock_settings.POSTGRES_USER = "user"
        mock_settings.POSTGRES_PASSWORD = "password"
        mock_settings.POSTGRES_PORT = 5432
        mock_settings.POSTGRES_DB = "testdb"
        
        config = get_tortoise_config()
        
        expected_url = "postgres://user:password@localhost:5432/testdb"
        assert config["connections"]["default"] == expected_url
