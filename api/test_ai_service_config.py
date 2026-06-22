"""Tests for AI provider resolution (no live API calls)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from api.ai_service import (
    AIConfigurationError,
    _normalize_openai_base_url,
    get_ai_settings,
    resolve_ai_provider,
)


class TestAIProviderResolution(unittest.TestCase):
    def setUp(self) -> None:
        self._env = {
            "AI_PROVIDER": "",
            "AZURE_OPENAI_ENDPOINT": "",
            "AZURE_OPENAI_API_KEY": "",
            "AZURE_OPENAI_CHAT_DEPLOYMENT": "",
            "AZURE_OPENAI_TRANSLATE_DEPLOYMENT": "",
            "AZURE_OPENAI_DEPLOYMENT": "",
            "AZURE_OPENAI_API_VERSION": "",
            "OPENAI_API_KEY": "",
            "OPENAI_CHAT_MODEL": "",
            "OPENAI_TRANSLATE_MODEL": "",
            "OPENAI_BASE_URL": "",
            "XAI_API_KEY": "",
            "XAI_CHAT_MODEL": "",
            "XAI_TRANSLATE_MODEL": "",
            "ENVIRONMENT": "",
            "AI_ALLOW_MOCK": "",
        }

    def _patch_env(self, overrides: dict[str, str] | None = None) -> dict[str, str]:
        env = dict(self._env)
        if overrides:
            env.update(overrides)
        return env

    def test_prefers_azure_when_credentials_present(self) -> None:
        env = self._patch_env(
            {
                "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "azure-key",
                "XAI_API_KEY": "xai-key",
            }
        )
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(resolve_ai_provider(), "azure")
            settings = get_ai_settings()
            self.assertEqual(settings.provider, "azure")
            self.assertEqual(settings.parse_model, "gpt-4o-mini")
            self.assertEqual(settings.translate_model, "gpt-4o")

    def test_azure_uses_custom_deployments(self) -> None:
        env = self._patch_env(
            {
                "AI_PROVIDER": "azure",
                "AZURE_OPENAI_ENDPOINT": "https://example.openai.azure.com/",
                "AZURE_OPENAI_API_KEY": "azure-key",
                "AZURE_OPENAI_CHAT_DEPLOYMENT": "hair-parse",
                "AZURE_OPENAI_TRANSLATE_DEPLOYMENT": "hair-translate",
            }
        )
        with patch.dict(os.environ, env, clear=False):
            settings = get_ai_settings()
            self.assertEqual(settings.parse_model, "hair-parse")
            self.assertEqual(settings.translate_model, "hair-translate")

    def test_explicit_openai_provider(self) -> None:
        env = self._patch_env(
            {
                "AI_PROVIDER": "openai",
                "OPENAI_API_KEY": "openai-key",
                "OPENAI_CHAT_MODEL": "gpt-4o-mini",
            }
        )
        with patch.dict(os.environ, env, clear=False):
            settings = get_ai_settings()
            self.assertEqual(settings.provider, "openai")
            self.assertEqual(settings.parse_model, "gpt-4o-mini")

    def test_bedrock_mantle_nemotron_settings(self) -> None:
        mantle_url = "https://bedrock-mantle.us-east-1.api.aws/v1"
        env = self._patch_env(
            {
                "AI_PROVIDER": "openai",
                "OPENAI_API_KEY": "bedrock-key",
                "OPENAI_BASE_URL": mantle_url,
                "OPENAI_CHAT_MODEL": "nvidia.nemotron-super-3-120b",
                "OPENAI_TRANSLATE_MODEL": "nvidia.nemotron-super-3-120b",
            }
        )
        with patch.dict(os.environ, env, clear=False):
            settings = get_ai_settings()
            self.assertEqual(settings.provider, "openai")
            self.assertEqual(settings.parse_model, "nvidia.nemotron-super-3-120b")
            self.assertEqual(settings.translate_model, "nvidia.nemotron-super-3-120b")
            self.assertEqual(settings.endpoint, mantle_url)

    def test_normalize_bedrock_runtime_url_to_openai_v1(self) -> None:
        normalized = _normalize_openai_base_url(
            "https://bedrock-runtime.us-east-1.amazonaws.com/compatible-apis/openai/v1"
        )
        self.assertEqual(
            normalized,
            "https://bedrock-runtime.us-east-1.amazonaws.com/openai/v1",
        )

    def test_passthrough_bedrock_mantle_url(self) -> None:
        mantle_url = "https://bedrock-mantle.us-east-1.api.aws/v1"
        self.assertEqual(_normalize_openai_base_url(mantle_url), mantle_url)

    def test_rejects_mock_in_production_without_override(self) -> None:
        env = self._patch_env({"ENVIRONMENT": "production"})
        with patch.dict(os.environ, env, clear=False):
            with self.assertRaises(AIConfigurationError):
                resolve_ai_provider()

    def test_allows_mock_in_production_when_explicitly_enabled(self) -> None:
        env = self._patch_env({"ENVIRONMENT": "production", "AI_ALLOW_MOCK": "1"})
        with patch.dict(os.environ, env, clear=False):
            self.assertEqual(resolve_ai_provider(), "mock")

    def test_explicit_mock_provider(self) -> None:
        env = self._patch_env({"AI_PROVIDER": "mock"})
        with patch.dict(os.environ, env, clear=False):
            settings = get_ai_settings()
            self.assertEqual(settings.provider, "mock")
            self.assertEqual(settings.parse_model, "offline-mock")


if __name__ == "__main__":
    unittest.main()
