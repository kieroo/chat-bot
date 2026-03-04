import unittest
from unittest.mock import patch

from app import web


class WebUiTests(unittest.TestCase):
    def test_parse_args_defaults(self) -> None:
        args = web.parse_args([])
        self.assertEqual(args.host, "0.0.0.0")
        self.assertEqual(args.port, 8000)

    def test_parse_args_custom(self) -> None:
        args = web.parse_args(["--host", "127.0.0.1", "--port", "9000"])
        self.assertEqual(args.host, "127.0.0.1")
        self.assertEqual(args.port, 9000)

    def test_main_returns_2_when_provider_init_fails(self) -> None:
        with patch("app.web.build_provider", side_effect=web.ProviderError("boom")):
            code = web.main(["--port", "0"])
        self.assertEqual(code, 2)


if __name__ == "__main__":
    unittest.main()
