"""
Purpose: Unit tests for serving adapter factory and backend resolution precedence.
Owner: Rajdeep (Architecture & Implementation)
Authority: Aligned with DEC-0014
"""

import pytest

from slokern.engine.serving.base import ConfigurationError
from slokern.engine.serving.factory import create_serving_adapter
from slokern.engine.serving.fake import FakeServingAdapter
from slokern.engine.serving.nebius import NebiusServingAdapter
from slokern.engine.serving.ollama import OllamaServingAdapter


def test_factory_precedence_cli(monkeypatch):
    """CLI argument takes highest precedence over environment variables and defaults."""
    monkeypatch.setenv("SLOKERN_ADAPTER", "fake")
    adapter = create_serving_adapter(backend="local")
    assert isinstance(adapter, OllamaServingAdapter)

    monkeypatch.setenv("SLOKERN_ADAPTER", "local")
    adapter = create_serving_adapter(backend="fake")
    assert isinstance(adapter, FakeServingAdapter)


def test_factory_precedence_env(monkeypatch):
    """SLOKERN_ADAPTER environment variable is respected when CLI argument is omitted."""
    monkeypatch.setenv("SLOKERN_ADAPTER", "fake")
    adapter = create_serving_adapter()
    assert isinstance(adapter, FakeServingAdapter)


def test_factory_default_local(monkeypatch):
    """Defaults to local Ollama adapter when no argument or env var is provided."""
    monkeypatch.delenv("SLOKERN_ADAPTER", raising=False)
    adapter = create_serving_adapter()
    assert isinstance(adapter, OllamaServingAdapter)
    assert adapter.model_name == "qwen3:4b-instruct-2507-q4_K_M"


def test_factory_unknown_backend():
    """Unknown backend raises ValueError."""
    with pytest.raises(ValueError) as exc_info:
        create_serving_adapter(backend="unknown_provider_xyz")
    assert "unknown serving backend" in str(exc_info.value).lower()


def test_factory_nebius_missing_credentials(monkeypatch):
    """Selecting Nebius without API key raises ConfigurationError with zero silent fallback."""
    monkeypatch.delenv("NEBIUS_API_KEY", raising=False)
    with pytest.raises(ConfigurationError) as exc_info:
        create_serving_adapter(backend="nebius")
    assert "Missing required credentials for Nebius backend" in str(exc_info.value)
    assert "Zero silent fallback" in str(exc_info.value)

    # When API key is provided, successfully returns NebiusServingAdapter
    adapter = create_serving_adapter(backend="nebius", api_key="test-key-12345")
    assert isinstance(adapter, NebiusServingAdapter)
    assert adapter.has_api_key is True
    assert adapter.model_name == "nvidia/NVIDIA-Nemotron-3-Nano-30B-A3B"


def test_factory_kwargs_isolation():
    """Local adapter cleanly ignores api_key ensuring credential isolation without TypeError."""
    adapter = create_serving_adapter(backend="local", api_key="neb_secret_key_12345")
    assert isinstance(adapter, OllamaServingAdapter)
    assert not hasattr(adapter, "_api_key")


def test_factory_fake_extra_kwargs():
    """Fake adapter cleanly ignores base_url and api_key without TypeError."""
    adapter = create_serving_adapter(
        backend="fake",
        base_url="http://127.0.0.1:11434",
        api_key="neb_secret_key_12345",
    )
    assert isinstance(adapter, FakeServingAdapter)
