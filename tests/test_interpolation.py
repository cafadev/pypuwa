"""Tests for the interpolation resolver."""

from dataclasses import dataclass

from pypuwa.interpolation import InterpolationResolver


@dataclass
class MockDatabase:
    NAME: str = "my_db"
    PORT: str = "5432"


@dataclass
class MockServices:
    database: MockDatabase = None

    def __post_init__(self):
        if self.database is None:
            self.database = MockDatabase()


@dataclass
class MockConfig:
    services: MockServices = None

    def __post_init__(self):
        if self.services is None:
            self.services = MockServices()


class TestInterpolationResolver:
    def test_simple_stack_interpolation(self):
        config = MockConfig()
        resolver = InterpolationResolver(
            config_data=config, stack_name="staging", environment_type="staging"
        )
        result = resolver.resolve_string("{stack}-my-service")
        assert result == "staging-my-service"

    def test_stack_name_interpolation(self):
        config = MockConfig()
        resolver = InterpolationResolver(
            config_data=config, stack_name="production", environment_type="production"
        )
        result = resolver.resolve_string("{stack_name}-db")
        assert result == "production-db"

    def test_complex_path_interpolation(self):
        config = MockConfig()
        resolver = InterpolationResolver(
            config_data=config, stack_name="staging", environment_type="staging"
        )
        result = resolver.resolve_string("${services.database.name}")
        assert result == "my_db"

    def test_unresolvable_path_preserved(self):
        config = MockConfig()
        resolver = InterpolationResolver(
            config_data=config, stack_name="staging", environment_type="staging"
        )
        result = resolver.resolve_string("${nonexistent.path}")
        assert result == "${nonexistent.path}"

    def test_resolve_object(self):
        @dataclass
        class ServiceConfig:
            SERVICE_NAME: str = "{stack}-backend"
            DB_NAME: str = "${services.database.name}"

        config = MockConfig()
        resolver = InterpolationResolver(
            config_data=config, stack_name="staging", environment_type="staging"
        )

        service = ServiceConfig()
        resolved = resolver.resolve(service)

        assert resolved.SERVICE_NAME == "staging-backend"
        assert resolved.DB_NAME == "my_db"

    def test_mixed_interpolation(self):
        config = MockConfig()
        resolver = InterpolationResolver(
            config_data=config, stack_name="prod", environment_type="production"
        )
        result = resolver.resolve_string("host-{stack}-${services.database.port}")
        assert result == "host-prod-5432"
