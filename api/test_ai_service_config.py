"""Tests for AI provider resolution (no live API calls)."""

from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from api.ai_service import AIConfigurationError, get_ai_settings, resolve_ai_provider


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
