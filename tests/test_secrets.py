"""Tests for the secrets module."""

from pypuwa.secrets import (
    Secret,
    get_secret_key,
    is_interpolation_reference,
    is_secret,
    secret,
)


class TestSecretMarker:
    def test_explicit_key(self):
        result = secret("MY_PASSWORD")
        assert result == "secret:MY_PASSWORD"

    def test_is_secret_true(self):
        assert is_secret("secret:DATABASE_PASSWORD") is True

    def test_is_secret_false(self):
        assert is_secret("not_a_secret") is False
        assert is_secret("") is False
        assert is_secret(123) is False

    def test_get_secret_key(self):
        assert get_secret_key("secret:MY_KEY") == "MY_KEY"
        assert get_secret_key("secret:${services.db.PASSWORD}") == "${services.db.PASSWORD}"

    def test_is_interpolation_reference(self):
        assert is_interpolation_reference("${services.db.PASSWORD}") is True
        assert is_interpolation_reference("${a}") is True
        assert is_interpolation_reference("not_a_ref") is False
        assert is_interpolation_reference("${incomplete") is False
        assert is_interpolation_reference(123) is False

    def test_cross_service_secret(self):
        result = secret("${services.redis.AUTH_TOKEN}")
        assert result == "secret:${services.redis.AUTH_TOKEN}"
        assert is_secret(result)
        key = get_secret_key(result)
        assert is_interpolation_reference(key)
