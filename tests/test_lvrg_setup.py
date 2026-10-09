"""Offline setup checks: python3 -m unittest discover -s tests -v.

Uses a temporary fake server, synthetic OAuth values, and no Slack/network calls.
"""

import json
import os
from pathlib import Path
import stat
import subprocess
import sys
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
LAUNCHER = ROOT / "scripts/lvrg-stdio.sh"
TOOLS = (
    "channels_list,conversations_history,conversations_replies,"
    "conversations_search_messages,conversations_add_message"
)


class LauncherTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="slack-setup-offline-")
        self.addCleanup(self.temporary.cleanup)
        self.directory = Path(self.temporary.name)
        self.binary = self.directory / "fake server"
        self.binary.write_text(
            f"#!{sys.executable}\n"
            "import json, os, sys\n"
            "print(json.dumps({'args': sys.argv[1:], 'env': "
            "{k: v for k, v in os.environ.items() if k.startswith('SLACK_MCP_')}}))\n"
            "sys.exit(int(os.environ.get('FAKE_EXIT', '0')))\n"
        )
        self.binary.chmod(0o700)
        self.environment = {
            "PATH": os.defpath,
            "HOME": str(self.directory),
            "SLACK_MCP_BINARY": str(self.binary),
            "SLACK_MCP_XOXP_TOKEN": "xoxp-offline-only",
            "SLACK_MCP_ADD_MESSAGE_TOOL": "C0123456789,G0123456789",
        }

    def run_launcher(self, changes=None, args=()):
        environment = self.environment.copy()
        for key, value in (changes or {}).items():
            if value is None:
                environment.pop(key, None)
            else:
                environment[key] = value
        return subprocess.run(
            ["/bin/sh", str(LAUNCHER), *args],
            env=environment,
            capture_output=True,
            text=True,
            timeout=10,
        )

    def test_shell_syntax(self):
        result = subprocess.run(
            ["/bin/sh", "-n", str(LAUNCHER)], capture_output=True, text=True
        )
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_explicit_policy_overrides_inherited_settings(self):
        result = self.run_launcher(
            {
                "SLACK_MCP_ENABLED_TOOLS": "conversations_add_message,reactions_add",
                "SLACK_MCP_ADD_MESSAGE_MARK": "true",
                "SLACK_MCP_ADD_MESSAGE_UNFURLING": "true",
                "SLACK_MCP_LOG_LEVEL": "debug",
                "SLACK_MCP_XOXB_TOKEN": "xoxb-offline-only",
                "SLACK_MCP_XOXC_TOKEN": "xoxc-offline-only",
                "SLACK_MCP_XOXD_TOKEN": "offline-only",
            },
            args=("--enabled-tools", "reactions_add"),
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        saved = json.loads(result.stdout)
        self.assertEqual(saved["args"], ["--transport", "stdio"])
        environment = saved["env"]
        self.assertEqual(environment["SLACK_MCP_ENABLED_TOOLS"], TOOLS)
        self.assertEqual(
            environment["SLACK_MCP_ADD_MESSAGE_TOOL"], "C0123456789,G0123456789"
        )
        self.assertEqual(environment["SLACK_MCP_XOXP_TOKEN"], self.environment["SLACK_MCP_XOXP_TOKEN"])
        for key in ("SLACK_MCP_XOXC_TOKEN", "SLACK_MCP_XOXD_TOKEN", "SLACK_MCP_XOXB_TOKEN"):
            self.assertNotIn(key, environment)
        self.assertEqual(environment["SLACK_MCP_LOG_LEVEL"], "warn")
        self.assertEqual(environment["SLACK_MCP_ADD_MESSAGE_MARK"], "false")
        self.assertEqual(environment["SLACK_MCP_ADD_MESSAGE_UNFURLING"], "false")
        state = self.directory / ".local/share/lvrg-slack-mcp"
        self.assertEqual(environment["SLACK_MCP_USERS_CACHE"], str(state / "users-cache.json"))
        self.assertEqual(environment["SLACK_MCP_CHANNELS_CACHE"], str(state / "channels-cache.json"))
        self.assertEqual(stat.S_IMODE(state.stat().st_mode), 0o700)

    def test_invalid_allowlists_never_start_server(self):
        for value in (
            None, "", "true", "1", "!C0123456789", "#general", "C123", "U0123456789",
            " C0123456789", "C0123456789, G0123456789", "C0123456789,",
            "C0123456789\ntrue", "C0123456789\n", "C0123456789;exit 0",
        ):
            with self.subTest(value=value):
                result = self.run_launcher({"SLACK_MCP_ADD_MESSAGE_TOOL": value})
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                self.assertNotIn(self.environment["SLACK_MCP_XOXP_TOKEN"], result.stderr)

    def test_invalid_oauth_values_never_start_server(self):
        for value in (
            None, "", "REPLACE_IN_PRIVATE_CONFIGURATION", "xoxb-offline", "demo",
            "xoxp-offline with spaces", "xoxp-offline\nvalue", "xoxp-$(exit 0)",
        ):
            with self.subTest(value=value):
                result = self.run_launcher({"SLACK_MCP_XOXP_TOKEN": value})
                self.assertNotEqual(result.returncode, 0)
                self.assertEqual(result.stdout, "")
                if value:
                    self.assertNotIn(value, result.stderr)

    def test_missing_or_nonexecutable_binary(self):
        result = self.run_launcher({"SLACK_MCP_BINARY": str(self.directory / "missing")})
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")
        self.binary.chmod(0o600)
        result = self.run_launcher()
        self.assertNotEqual(result.returncode, 0)
        self.assertEqual(result.stdout, "")

    def test_custom_state_directory_and_server_exit(self):
        state = self.directory / "custom state"
        result = self.run_launcher({"SLACK_MCP_STATE_DIR": str(state), "FAKE_EXIT": "23"})
        self.assertEqual(result.returncode, 23)
        saved = json.loads(result.stdout)
        self.assertEqual(saved["env"]["SLACK_MCP_USERS_CACHE"], str(state / "users-cache.json"))


class ExampleTests(unittest.TestCase):
    def test_manifest_user_scopes(self):
        manifest = json.loads((ROOT / "examples/lvrg-slack-app-manifest.json").read_text())
        scopes = manifest["oauth_config"]["scopes"]
        self.assertEqual(set(scopes), {"user"})
        self.assertEqual(set(scopes["user"]), {
            "channels:read", "channels:history", "groups:read", "groups:history",
            "im:read", "mpim:read", "users:read", "search:read", "chat:write",
        })
        self.assertEqual(len(scopes["user"]), 9)
        self.assertFalse(manifest["settings"]["token_rotation_enabled"])

    def test_overlay_is_placeholder_only(self):
        overlay = json.loads((ROOT / "examples/lvrg-codex-overlay.json").read_text())
        self.assertEqual(set(overlay), {"mcpServers"})
        self.assertEqual(set(overlay["mcpServers"]), {"slack-direct"})
        server = overlay["mcpServers"]["slack-direct"]
        self.assertEqual(server["command"], "/bin/sh")
        self.assertEqual(server["args"], ["/ABSOLUTE/PATH/TO/slack-mcp-server/scripts/lvrg-stdio.sh"])
        self.assertEqual(server["env"], {
            "SLACK_MCP_XOXP_TOKEN": "REPLACE_IN_PRIVATE_CONFIGURATION",
            "SLACK_MCP_ADD_MESSAGE_TOOL": "C0123456789",
        })
        self.assertGreaterEqual(server["startup_timeout_sec"], 1)
        self.assertGreaterEqual(server["tool_timeout_sec"], 1)


if __name__ == "__main__":
    unittest.main()
