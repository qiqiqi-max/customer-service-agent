import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import observability


class TestObservability(unittest.TestCase):
    def tearDown(self):
        observability.reset_observability()

    def test_log_event_writes_json_and_filters_secrets(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            observability.reset_observability()
            with patch("config.log_dir", tmp_dir):
                observability.log_event(
                    "test.event",
                    api_key="secret-value",
                    nested={"token": "secret-token", "safe": "visible"},
                )
                observability.reset_observability()

            log_path = Path(tmp_dir) / "app.log"
            payload = json.loads(log_path.read_text(encoding="utf-8").splitlines()[0])

        self.assertEqual(payload["event"], "test.event")
        self.assertNotIn("api_key", payload)
        self.assertEqual(payload["nested"], {"safe": "visible"})


if __name__ == "__main__":
    unittest.main()
