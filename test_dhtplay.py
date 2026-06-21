#!/usr/bin/env python3
"""
dhtplay test suite
==================
Each scenario has explicit success criteria (PASS / FAIL).
Run:  python3 test_dhtplay.py
"""

import base64
import importlib.util
import os
import subprocess
import sys
import textwrap
import unittest
from unittest.mock import MagicMock, patch

# ---------------------------------------------------------------------------
# Load the module from the sibling file "dhtplay" (no .py extension)
# ---------------------------------------------------------------------------
_HERE = os.path.dirname(os.path.abspath(__file__))
_SCRIPT = os.path.join(_HERE, "dhtplay")

from importlib.machinery import SourceFileLoader
dhtplay = SourceFileLoader("dhtplay", _SCRIPT).load_module()

# Shorthand
parse_infohash  = dhtplay.parse_infohash
build_magnet    = dhtplay.build_magnet
find_webtorrent = dhtplay.find_webtorrent
main            = dhtplay.main

# A well-known, safe public-domain test vector (Ubuntu 22.04 amd64 ISO)
UBUNTU_HEX   = "3b23568e2f9f2eecbcbcbd2b7f54c5a2a6b01a2a"   # fictional — safe for tests
UBUNTU_HEX_R = "3b23568e2f9f2eecbcbcbd2b7f54c5a2a6b01a2a"   # same
# base32 of a 20-byte value
_20BYTES    = bytes.fromhex("aabbccddee" * 4)               # 20 bytes
B32_IH      = base64.b32encode(_20BYTES).decode()           # 32 chars
B32_HEX_EXP = _20BYTES.hex()


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------
def run_main(*args, vlc_side_effect=None):
    """
    Run main() with the given CLI args.
    Patches subprocess.Popen to prevent actually launching VLC.
    Returns (exit_code, stdout_lines, stderr_lines).
    """
    import io
    from contextlib import redirect_stdout, redirect_stderr

    popen_mock = MagicMock()
    if vlc_side_effect:
        popen_mock.side_effect = vlc_side_effect

    out_buf = io.StringIO()
    err_buf = io.StringIO()

    with patch("dhtplay.subprocess.Popen", popen_mock), \
         patch("dhtplay.find_webtorrent", return_value="/opt/homebrew/bin/webtorrent"), \
         redirect_stdout(out_buf), redirect_stderr(err_buf):
        try:
            rc = main(list(args))
        except SystemExit as e:
            rc = e.code if isinstance(e.code, int) else 1

    return rc, out_buf.getvalue().splitlines(), err_buf.getvalue().splitlines()


# ===========================================================================
# S1 — Basic 40-char hex infohash accepted
# ===========================================================================
class S01_HexInfohash(unittest.TestCase):
    """CRITERIA: parse_infohash returns lowercase hex unchanged for valid 40-char input."""

    def test_lowercase_hex_passthrough(self):
        result = parse_infohash("aabbccddee" * 4)
        self.assertEqual(result, "aabbccddee" * 4)

    def test_uppercase_hex_normalised(self):
        result = parse_infohash("AABBCCDDEE" * 4)
        self.assertEqual(result, "aabbccddee" * 4)

    def test_mixed_case_hex_normalised(self):
        result = parse_infohash("AaBbCcDdEe" * 4)
        self.assertEqual(result, "aabbccddee" * 4)


# ===========================================================================
# S2 — 32-char base32 infohash decoded correctly
# ===========================================================================
class S02_Base32Infohash(unittest.TestCase):
    """CRITERIA: parse_infohash converts 32-char base32 to 40-char hex."""

    def test_base32_roundtrip(self):
        result = parse_infohash(B32_IH)
        self.assertEqual(result, B32_HEX_EXP)

    def test_lowercase_base32_accepted(self):
        result = parse_infohash(B32_IH.lower())
        self.assertEqual(result, B32_HEX_EXP)


# ===========================================================================
# S3 — Magnet URI input: infohash extracted
# ===========================================================================
class S03_MagnetURIInput(unittest.TestCase):
    """CRITERIA: parse_infohash handles a full magnet URI and extracts the btih."""

    def test_magnet_hex_btih(self):
        ih = "aabbccddee" * 4
        magnet = f"magnet:?xt=urn:btih:{ih}&dn=Test"
        self.assertEqual(parse_infohash(magnet), ih)

    def test_magnet_base32_btih(self):
        magnet = f"magnet:?xt=urn:btih:{B32_IH}&dn=Test"
        self.assertEqual(parse_infohash(magnet), B32_HEX_EXP)


# ===========================================================================
# S4 — Invalid infohash rejected with clear error
# ===========================================================================
class S04_InvalidInfohash(unittest.TestCase):
    """CRITERIA: parse_infohash raises ValueError with a descriptive message."""

    def _assert_value_error(self, ih):
        with self.assertRaises(ValueError):
            parse_infohash(ih)

    def test_too_short_hex(self):
        self._assert_value_error("aabbcc")

    def test_too_long_hex(self):
        self._assert_value_error("aabbccddee" * 4 + "00")

    def test_non_hex_characters(self):
        self._assert_value_error("zzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzzz")

    def test_empty_string(self):
        self._assert_value_error("")

    def test_random_word(self):
        self._assert_value_error("notaninfohash")

    def test_magnet_with_no_btih(self):
        self._assert_value_error("magnet:?dn=NoHash")


# ===========================================================================
# S5 — Magnet URI built correctly (with trackers)
# ===========================================================================
class S05_MagnetURIConstruction(unittest.TestCase):
    """CRITERIA: build_magnet produces a URI starting with magnet:?xt=urn:btih:<hex>."""

    IH = "aabbccddee" * 4

    def test_basic_uri_prefix(self):
        uri = build_magnet(self.IH)
        self.assertTrue(uri.startswith(f"magnet:?xt=urn:btih:{self.IH}"))

    def test_trackers_appended(self):
        uri = build_magnet(self.IH, trackers=["udp://example.com:1234/announce"])
        self.assertIn("tr=", uri)
        self.assertIn("example.com", uri)

    def test_display_name_appended(self):
        uri = build_magnet(self.IH, display_name="My Movie")
        self.assertIn("dn=", uri)
        self.assertIn("My%20Movie", uri)

    def test_no_trackers_when_empty(self):
        uri = build_magnet(self.IH, trackers=[])
        self.assertNotIn("tr=", uri)


# ===========================================================================
# S6 — --dry-run prints URI and exits 0, does not launch VLC
# ===========================================================================
class S06_DryRun(unittest.TestCase):
    """CRITERIA: --dry-run prints the magnet URI to stdout and returns exit code 0."""

    IH = "aabbccddee" * 4

    def test_prints_magnet_uri(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main([self.IH, "--dry-run"])
        output = buf.getvalue()
        self.assertEqual(rc, 0)
        self.assertIn(f"urn:btih:{self.IH}", output)

    def test_no_vlc_launched(self):
        popen_mock = MagicMock()
        import io
        from contextlib import redirect_stdout
        with patch("dhtplay.subprocess.Popen", popen_mock), \
             redirect_stdout(io.StringIO()):
            main([self.IH, "--dry-run"])
        popen_mock.assert_not_called()


# ===========================================================================
# S7 — --no-trackers omits tracker params
# ===========================================================================
class S07_NoTrackers(unittest.TestCase):
    """CRITERIA: --no-trackers produces a URI without tr= parameters."""

    IH = "aabbccddee" * 4

    def test_no_trackers_in_uri(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = main([self.IH, "--dry-run", "--no-trackers"])
        self.assertEqual(rc, 0)
        self.assertNotIn("tr=", buf.getvalue())

    def test_default_has_trackers(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main([self.IH, "--dry-run"])
        self.assertIn("tr=", buf.getvalue())


# ===========================================================================
# S8 — --name sets dn= in the URI
# ===========================================================================
class S08_DisplayName(unittest.TestCase):
    """CRITERIA: --name encodes the display name as dn= in the magnet URI."""

    IH = "aabbccddee" * 4

    def test_name_appears_in_uri(self):
        import io
        from contextlib import redirect_stdout
        buf = io.StringIO()
        with redirect_stdout(buf):
            main([self.IH, "--dry-run", "--name", "Blade Runner"])
        self.assertIn("dn=", buf.getvalue())
        self.assertIn("Blade", buf.getvalue())

    def test_spaces_percent_encoded(self):
        uri = build_magnet(self.IH, display_name="Hello World")
        self.assertIn("Hello%20World", uri)


# ===========================================================================
# S9 — webtorrent not found returns exit code 2 with helpful message
# ===========================================================================
class S09_WebtorrentNotFound(unittest.TestCase):
    """CRITERIA: exit code 2 and stderr message suggesting 'npm install -g webtorrent-cli'."""

    IH = "aabbccddee" * 4

    def test_exit_code_2(self):
        import io
        from contextlib import redirect_stderr
        err = io.StringIO()
        with patch("dhtplay.find_webtorrent", return_value=None), \
             redirect_stderr(err):
            try:
                rc = main([self.IH])
            except SystemExit as e:
                rc = e.code
        self.assertEqual(rc, 2)

    def test_helpful_message(self):
        import io
        from contextlib import redirect_stderr
        err = io.StringIO()
        with patch("dhtplay.find_webtorrent", return_value=None), \
             redirect_stderr(err):
            try:
                main([self.IH])
            except SystemExit:
                pass
        self.assertIn("webtorrent-cli", err.getvalue())


# ===========================================================================
# S10 — find_webtorrent() resolution logic: hardcoded candidates before `which`
# ===========================================================================
class S10_WebtorrentFound(unittest.TestCase):
    """CRITERIA: find_webtorrent() prefers hardcoded candidates over `which` fallback."""

    def test_hardcoded_candidate_preferred(self):
        # When a hardcoded candidate exists, it is returned without calling `which`
        with patch("dhtplay._executable", side_effect=lambda p: p == "/opt/homebrew/bin/webtorrent"), \
             patch("dhtplay.subprocess.run") as run_mock:
            result = find_webtorrent()
        self.assertEqual(result, "/opt/homebrew/bin/webtorrent")
        run_mock.assert_not_called()

    def test_which_fallback_used_when_no_candidates(self):
        # When no hardcoded candidates are executable, `which` fallback is tried
        run_result = MagicMock()
        run_result.returncode = 0
        run_result.stdout = "/usr/bin/webtorrent\n"
        with patch("dhtplay._executable", return_value=False), \
             patch("dhtplay.subprocess.run", return_value=run_result):
            result = find_webtorrent()
        self.assertEqual(result, "/usr/bin/webtorrent")


# ===========================================================================
# S11 — webtorrent launched with the magnet URI and --vlc flag
# ===========================================================================
class S11_WebtorrentLaunched(unittest.TestCase):
    """CRITERIA: subprocess.Popen is called with [webtorrent_path, magnet_uri, '--vlc']."""

    IH = "aabbccddee" * 4
    WT = "/opt/homebrew/bin/webtorrent"

    def test_popen_called_with_magnet(self):
        popen_mock = MagicMock()
        import io
        from contextlib import redirect_stdout
        with patch("dhtplay.subprocess.Popen", popen_mock), \
             patch("dhtplay.find_webtorrent", return_value=self.WT), \
             redirect_stdout(io.StringIO()):
            rc = main([self.IH])
        self.assertEqual(rc, 0)
        popen_mock.assert_called_once()
        call_args = popen_mock.call_args[0][0]
        self.assertEqual(call_args[0], self.WT)
        self.assertIn(f"urn:btih:{self.IH}", call_args[1])
        self.assertEqual(call_args[2], "--vlc")

    def test_popen_failure_returns_exit_3(self):
        import io
        from contextlib import redirect_stderr
        err = io.StringIO()
        with patch("dhtplay.subprocess.Popen", side_effect=OSError("exec failed")), \
             patch("dhtplay.find_webtorrent", return_value=self.WT), \
             redirect_stderr(err):
            try:
                rc = main([self.IH])
            except SystemExit as e:
                rc = e.code
        self.assertEqual(rc, 3)


# ===========================================================================
# S12 — CLI end-to-end via subprocess (smoke test)
# ===========================================================================
class S12_CLIEndToEnd(unittest.TestCase):
    """CRITERIA: running the script via subprocess with --dry-run exits 0 and prints a magnet URI."""

    IH = "aabbccddee" * 4

    def test_subprocess_dry_run(self):
        result = subprocess.run(
            [sys.executable, _SCRIPT, self.IH, "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, msg=result.stderr)
        self.assertIn("magnet:?xt=urn:btih:", result.stdout)

    def test_subprocess_invalid_hash_nonzero(self):
        result = subprocess.run(
            [sys.executable, _SCRIPT, "notvalid", "--dry-run"],
            capture_output=True, text=True,
        )
        self.assertNotEqual(result.returncode, 0)

    def test_subprocess_help_exits_0(self):
        result = subprocess.run(
            [sys.executable, _SCRIPT, "--help"],
            capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0)
        self.assertIn("infohash", result.stdout)


# ===========================================================================
# S13 — --url flag reads real stream URL from webtorrent stdout, substitutes LAN IP
# ===========================================================================
class S13_UrlFlag(unittest.TestCase):
    """CRITERIA: --url constructs URL from known webtorrent path pattern, no stdout piping, exit 0."""

    IH = "aabbccddee" * 4
    WT = "/opt/homebrew/bin/webtorrent"

    def test_url_flag_prints_http_url_with_infohash(self):
        import io
        from contextlib import redirect_stdout
        proc_mock = MagicMock()
        proc_mock.wait.return_value = None
        popen_mock = MagicMock(return_value=proc_mock)
        out = io.StringIO()
        with patch("dhtplay.subprocess.Popen", popen_mock), \
             patch("dhtplay.find_webtorrent", return_value=self.WT), \
             patch("dhtplay.get_lan_ip", return_value="192.168.1.100"), \
             patch("dhtplay._render_qr"), \
             redirect_stdout(out):
            rc = main([self.IH, "--url"])
        self.assertEqual(rc, 0)
        output = out.getvalue()
        self.assertIn("192.168.1.100", output)
        self.assertIn(self.IH, output)
        self.assertNotIn("localhost", output)

    def test_url_flag_no_vlc(self):
        import io
        from contextlib import redirect_stdout
        proc_mock = MagicMock()
        proc_mock.wait.return_value = None
        popen_mock = MagicMock(return_value=proc_mock)
        out = io.StringIO()
        with patch("dhtplay.subprocess.Popen", popen_mock), \
             patch("dhtplay.find_webtorrent", return_value=self.WT), \
             patch("dhtplay.get_lan_ip", return_value="192.168.1.100"), \
             patch("dhtplay._render_qr"), \
             redirect_stdout(out):
            rc = main([self.IH, "--url"])
        self.assertEqual(rc, 0)
        call_args = popen_mock.call_args[0][0]
        self.assertNotIn("--vlc", call_args)

    def test_url_flag_popen_not_piped(self):
        # stdout must NOT be piped — piping suppresses webtorrent's TUI and causes early exit
        import io
        from contextlib import redirect_stdout
        captured_kwargs = {}
        proc_mock = MagicMock()
        proc_mock.wait.return_value = None
        def capturing_popen(cmd, **kwargs):
            captured_kwargs.update(kwargs)
            return proc_mock
        out = io.StringIO()
        with patch("dhtplay.subprocess.Popen", capturing_popen), \
             patch("dhtplay.find_webtorrent", return_value=self.WT), \
             patch("dhtplay.get_lan_ip", return_value="192.168.1.100"), \
             patch("dhtplay._render_qr"), \
             redirect_stdout(out):
            main([self.IH, "--url"])
        self.assertNotIn("stdout", captured_kwargs)


# ===========================================================================
# S14 — --url keyboard interrupt causes proc.terminate()
# ===========================================================================
class S14_UrlKeyboardInterrupt(unittest.TestCase):
    """CRITERIA: KeyboardInterrupt from proc.wait() causes proc.terminate() to be called once."""

    IH = "aabbccddee" * 4
    WT = "/opt/homebrew/bin/webtorrent"

    def test_keyboard_interrupt_calls_terminate(self):
        import io
        from contextlib import redirect_stdout
        proc_mock = MagicMock()
        proc_mock.wait.side_effect = KeyboardInterrupt
        popen_mock = MagicMock(return_value=proc_mock)
        out = io.StringIO()
        with patch("dhtplay.subprocess.Popen", popen_mock), \
             patch("dhtplay.find_webtorrent", return_value=self.WT), \
             patch("dhtplay.get_lan_ip", return_value="127.0.0.1"), \
             patch("dhtplay._render_qr"), \
             redirect_stdout(out):
            rc = main([self.IH, "--url"])
        self.assertEqual(rc, 0)
        proc_mock.terminate.assert_called_once()


# ===========================================================================
# S15 — --port flag value reaches the Popen command list
# ===========================================================================
class S15_PortFlag(unittest.TestCase):
    """CRITERIA: integer passed via --port appears alongside -p in Popen call args."""

    IH = "aabbccddee" * 4
    WT = "/opt/homebrew/bin/webtorrent"

    def test_port_value_in_popen_args(self):
        import io
        from contextlib import redirect_stdout
        popen_mock = MagicMock()
        out = io.StringIO()
        with patch("dhtplay.subprocess.Popen", popen_mock), \
             patch("dhtplay.find_webtorrent", return_value=self.WT), \
             redirect_stdout(out):
            rc = main([self.IH, "--port", "9999"])
        self.assertEqual(rc, 0)
        call_args = popen_mock.call_args[0][0]
        self.assertIn("-p", call_args)
        self.assertIn("9999", call_args)


# ===========================================================================
# S16 — get_lan_ip() unit tests: ipconfig, socket fallback, OSError fallback
# ===========================================================================
class S16_GetLanIp(unittest.TestCase):
    """CRITERIA: get_lan_ip() returns the correct IP for all three code paths."""

    def test_ipconfig_success(self):
        # ipconfig returns an IP for en0 — function returns that IP
        result_mock = MagicMock()
        result_mock.stdout = "192.168.1.42\n"
        with patch("dhtplay.subprocess.run", return_value=result_mock):
            ip = dhtplay.get_lan_ip()
        self.assertEqual(ip, "192.168.1.42")

    def test_socket_fallback_when_ipconfig_fails(self):
        # All ipconfig calls return empty stdout — socket path succeeds
        fail_result = MagicMock()
        fail_result.stdout = ""
        sock_mock = MagicMock()
        sock_mock.getsockname.return_value = ("10.0.0.5", 0)
        with patch("dhtplay.subprocess.run", return_value=fail_result), \
             patch("socket.socket", return_value=sock_mock):
            ip = dhtplay.get_lan_ip()
        self.assertEqual(ip, "10.0.0.5")

    def test_oserror_returns_localhost(self):
        # All ipconfig calls fail; socket.socket() raises OSError — returns 127.0.0.1
        fail_result = MagicMock()
        fail_result.stdout = ""
        with patch("dhtplay.subprocess.run", return_value=fail_result), \
             patch("socket.socket", side_effect=OSError("no socket")):
            ip = dhtplay.get_lan_ip()
        self.assertEqual(ip, "127.0.0.1")


# ===========================================================================
# S17 — qrencode present: subprocess.run called with qrencode args
# ===========================================================================
class S17_QrCode(unittest.TestCase):
    """CRITERIA: when qrencode is available, subprocess.run is called with the right args."""

    IH = "aabbccddee" * 4
    WT = "/opt/homebrew/bin/webtorrent"

    def test_qrencode_called_with_url(self):
        import io
        from contextlib import redirect_stdout
        proc_mock = MagicMock()
        proc_mock.wait.return_value = None
        popen_mock = MagicMock(return_value=proc_mock)
        run_mock = MagicMock()
        out = io.StringIO()
        with patch("dhtplay.subprocess.Popen", popen_mock), \
             patch("dhtplay.find_webtorrent", return_value=self.WT), \
             patch("dhtplay.get_lan_ip", return_value="192.168.1.100"), \
             patch("dhtplay.subprocess.run", run_mock), \
             redirect_stdout(out):
            rc = main([self.IH, "--url"])
        self.assertEqual(rc, 0)
        expected_url = f"http://192.168.1.100:8888/webtorrent/{self.IH}/"
        run_mock.assert_called_once_with(
            ["qrencode", "-t", "ansiutf8", expected_url]
        )


# ===========================================================================
# S18 — qrencode absent: FileNotFoundError swallowed, exit 0, stderr empty
# ===========================================================================
class S18_QrCodeAbsent(unittest.TestCase):
    """CRITERIA: when qrencode raises FileNotFoundError, exit code is 0 and stderr is empty."""

    IH = "aabbccddee" * 4
    WT = "/opt/homebrew/bin/webtorrent"

    def test_qrencode_absent_no_error(self):
        import io
        from contextlib import redirect_stdout, redirect_stderr
        proc_mock = MagicMock()
        proc_mock.wait.return_value = None
        popen_mock = MagicMock(return_value=proc_mock)
        out = io.StringIO()
        err = io.StringIO()
        with patch("dhtplay.subprocess.Popen", popen_mock), \
             patch("dhtplay.find_webtorrent", return_value=self.WT), \
             patch("dhtplay.get_lan_ip", return_value="192.168.1.100"), \
             patch("dhtplay.subprocess.run", side_effect=FileNotFoundError("qrencode not found")), \
             redirect_stdout(out), redirect_stderr(err):
            rc = main([self.IH, "--url"])
        self.assertEqual(rc, 0)
        self.assertEqual(err.getvalue(), "")


# ---------------------------------------------------------------------------
# Runner with pretty PASS / FAIL summary
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    loader = unittest.TestLoader()
    suite  = loader.loadTestsFromModule(sys.modules[__name__])
    runner = unittest.TextTestRunner(verbosity=2, stream=sys.stdout)
    result = runner.run(suite)

    print()
    total  = result.testsRun
    failed = len(result.failures) + len(result.errors)
    passed = total - failed
    print(f"{'='*60}")
    print(f"  RESULTS: {passed}/{total} passed", end="")
    if failed:
        print(f"  ({failed} FAILED)")
    else:
        print("  — ALL PASS")
    print(f"{'='*60}")

    sys.exit(0 if result.wasSuccessful() else 1)
