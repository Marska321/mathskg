import importlib
import sys

import pytest
from fastapi.testclient import TestClient


def _reload_module(module_name: str):
    if module_name in sys.modules:
        return importlib.reload(sys.modules[module_name])
    return importlib.import_module(module_name)


def test_importing_config_and_database_does_not_require_env(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    monkeypatch.delenv('SUPABASE_KEY', raising=False)

    config = _reload_module('core.config')
    database = _reload_module('core.database')

    config.reset_settings_cache()
    database.reset_supabase_cache()
    monkeypatch.setattr(config, '_ensure_dotenv_loaded', lambda: None)

    assert hasattr(config, 'get_settings')
    assert repr(database.supabase) == '<LazySupabaseProxy>'


def test_get_settings_supports_legacy_supabase_key_alias(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    monkeypatch.setenv('SUPABASE_KEY', 'legacy-key')

    config = _reload_module('core.config')
    config.reset_settings_cache()
    monkeypatch.setattr(config, '_ensure_dotenv_loaded', lambda: None)

    settings = config.get_settings()

    assert settings.supabase_url == 'https://example.supabase.co'
    assert settings.supabase_service_key == 'legacy-key'
    assert config.get_required_env('SUPABASE_SERVICE_KEY') == 'legacy-key'
    assert config.get_required_env('SUPABASE_KEY') == 'legacy-key'


def test_service_role_key_takes_precedence_over_legacy_alias(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_KEY', 'service-key')
    monkeypatch.setenv('SUPABASE_KEY', 'legacy-key')

    config = _reload_module('core.config')
    config.reset_settings_cache()
    monkeypatch.setattr(config, '_ensure_dotenv_loaded', lambda: None)

    settings = config.get_settings()

    assert settings.supabase_service_key == 'service-key'
    assert config.get_required_env('SUPABASE_KEY') == 'service-key'


def test_get_supabase_is_lazy_and_cached(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_KEY', 'service-key')
    monkeypatch.delenv('SUPABASE_KEY', raising=False)

    config = _reload_module('core.config')
    database = _reload_module('core.database')
    config.reset_settings_cache()
    database.reset_supabase_cache()
    monkeypatch.setattr(config, '_ensure_dotenv_loaded', lambda: None)

    calls: list[tuple[str, str]] = []

    class FakeClient:
        def table(self, _: str):
            return self

    def fake_create_client(url: str, key: str):
        calls.append((url, key))
        return FakeClient()

    monkeypatch.setattr(database, 'create_client', fake_create_client)

    assert calls == []
    first = database.get_supabase()
    second = database.get_supabase()

    assert first is second
    assert calls == [('https://example.supabase.co', 'service-key')]
    assert database.supabase.table('student_mastery') is first


def test_main_imports_cleanly_and_validates_on_startup(monkeypatch):
    monkeypatch.delenv('SUPABASE_URL', raising=False)
    monkeypatch.delenv('SUPABASE_SERVICE_KEY', raising=False)
    monkeypatch.delenv('SUPABASE_KEY', raising=False)

    config = _reload_module('core.config')
    database = _reload_module('core.database')
    config.reset_settings_cache()
    database.reset_supabase_cache()
    monkeypatch.setattr(config, '_ensure_dotenv_loaded', lambda: None)
    main = _reload_module('main')

    with pytest.raises(config.ConfigError):
        with TestClient(main.app):
            pass


def test_main_startup_initializes_settings_and_database(monkeypatch):
    monkeypatch.setenv('SUPABASE_URL', 'https://example.supabase.co')
    monkeypatch.setenv('SUPABASE_SERVICE_KEY', 'service-key')

    config = _reload_module('core.config')
    database = _reload_module('core.database')
    config.reset_settings_cache()
    database.reset_supabase_cache()
    monkeypatch.setattr(config, '_ensure_dotenv_loaded', lambda: None)
    main = _reload_module('main')

    calls = {'settings': 0, 'database': 0}

    real_get_settings = main.get_settings

    def fake_get_settings():
        calls['settings'] += 1
        return real_get_settings()

    class FakeClient:
        pass

    def fake_get_supabase():
        calls['database'] += 1
        return FakeClient()

    monkeypatch.setattr(main, 'get_settings', fake_get_settings)
    monkeypatch.setattr(main, 'get_supabase', fake_get_supabase)

    with TestClient(main.app):
        pass

    assert calls == {'settings': 1, 'database': 1}
