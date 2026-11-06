"""The assistant's observation entry point must not reach mutating providers."""
import contextlib
import importlib.machinery
import io
import pathlib
import unittest
from unittest.mock import patch

cap = importlib.machinery.SourceFileLoader(
    "cap_assistant_test", str(pathlib.Path(__file__).resolve().parents[1] / "bin/cap")
).load_module()


class ObserveGate(unittest.TestCase):
    def test_only_channel_free_observations_reach_act(self):
        actions = {
            "system.battery": {"mutating": False, "consequence": "observe"},
            "desktop.move": {"mutating": True, "consequence": "adjust"},
            "interests.fetch": {"mutating": False, "consequence": "report", "channels": ["net:example.com"]},
            "agent.resolve": {"mutating": False, "consequence": "observe"},
            "network.read": {"mutating": False, "consequence": "observe", "channels": ["net:example.com"]},
            "missing.metadata": {},
        }
        with patch.object(cap, "actions", return_value=actions), patch.object(cap, "cmd_act", return_value=0) as act:
            self.assertEqual(cap.cmd_observe(["system.battery"]), 0)
            for name in ("desktop.move", "interests.fetch", "agent.resolve", "network.read", "missing.metadata", "unknown"):
                with self.subTest(name=name), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(cap.cmd_observe([name]), 1)
            act.assert_called_once_with(["system.battery"])


if __name__ == "__main__":
    unittest.main()
