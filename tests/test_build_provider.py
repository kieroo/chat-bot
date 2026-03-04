import unittest

from app.config import Settings
from app.providers import OllamaProvider, ProviderError, build_provider


class BuildProviderTests(unittest.TestCase):
    def test_build_provider_ollama_success(self) -> None:
        settings = Settings(provider="ollama", model="qwen2.5:7b")
        provider = build_provider(settings)
        self.assertIsInstance(provider, OllamaProvider)

    def test_build_provider_invalid_provider(self) -> None:
        settings = Settings(provider="unknown")
        with self.assertRaises(ProviderError):
            build_provider(settings)


if __name__ == "__main__":
    unittest.main()
