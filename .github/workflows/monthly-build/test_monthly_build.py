"""Test monthly build failures without submitting builds."""

import contextlib
import io
import os
import runpy
import subprocess
import sys
import tempfile
import types
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).parent


class MonthlyBuildTests(unittest.TestCase):
    def test_copr_command_failure(self):
        with tempfile.TemporaryDirectory() as temporary:
            directory = Path(temporary)
            config = directory / "config"
            script = directory / "build-copr.sh"
            script.write_text(
                (SCRIPTS / "build-copr.sh").read_text().replace("$HOME/.config", str(config))
            )
            packit = directory / "packit"
            packit.write_text(
                '#!/bin/sh\n'
                'test -z "${COPR_CONFIG+x}" || exit 24\n'
                'test -f "$RHC_TEST_CONFIG" || exit 25\n'
                'test "$(stat -c %a "$RHC_TEST_CONFIG")" = 600 || exit 26\n'
                'echo "SRPM creation failed"\n'
                'exit 23\n'
            )
            packit.chmod(0o755)
            result = subprocess.run(
                ["bash", str(script)],
                cwd=directory,
                env={
                    **os.environ,
                    "PATH": f"{directory}:{os.environ['PATH']}",
                    "COPR_CONFIG": "test-only credentials",
                    "COPR_OWNER": "test",
                    "COPR_PROJECT": "rhc",
                    "RHC_TEST_CONFIG": str(config / "copr"),
                },
                capture_output=True,
                text=True,
            )
            self.assertEqual(result.returncode, 23, result.stderr)
            self.assertFalse((config / "copr").exists())
            self.assertIn("SRPM creation failed", (directory / "packit-build.log").read_text())

    def test_copr_results(self):
        targets = ["rhel-10-aarch64", "rhel-10-x86_64"]
        cases = [
            ("succeeded", targets, "succeeded", "Build id: 123, repo url: test", False),
            ("failed", targets, "succeeded", "Build id: 123, repo url: test", True),
            ("running", targets, "succeeded", "Build id: 123, repo url: test", True),
            ("succeeded", targets[:1], "succeeded", "Build id: 123, repo url: test", True),
            ("succeeded", targets, "failed", "Build id: 123, repo url: test", True),
            ("succeeded", targets, "succeeded", "No build ID", True),
            ("succeeded", targets, "succeeded", "Build id: 123,\nBuild id: 456,", True),
        ]
        for state, chroots, target_state, log, fails in cases:
            with self.subTest(
                state=state, chroots=chroots, target_state=target_state, log=log
            ):
                client = Mock()
                client.config = {"copr_url": "https://copr.example.test/"}
                client.build_proxy.get.return_value = types.SimpleNamespace(
                    state=state, chroots=chroots
                )
                client.build_chroot_proxy.get.return_value = types.SimpleNamespace(
                    state=target_state, result_url="https://copr.example.test/results/"
                )
                copr = types.ModuleType("copr")
                v3 = types.ModuleType("copr.v3")
                v3.Client = Mock()
                v3.Client.create_from_config_file.return_value = client
                with tempfile.TemporaryDirectory() as temporary:
                    output = Path(temporary) / "output"
                    expected = (
                        self.assertRaises(SystemExit) if fails else contextlib.nullcontext()
                    )
                    with (
                        patch.dict(sys.modules, {"copr": copr, "copr.v3": v3}),
                        patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}),
                        patch.object(Path, "read_text", return_value=log),
                        contextlib.redirect_stdout(io.StringIO()),
                        expected,
                    ):
                        runpy.run_path(str(SCRIPTS / "check-copr.py"))
                    if not fails:
                        self.assertEqual(
                            output.read_text(),
                            "build_url=https://copr.example.test/coprs/build/123/\n",
                        )
                        client.build_proxy.get.assert_called_once_with(123)
                        self.assertEqual(client.build_chroot_proxy.get.call_count, 2)

    def test_source_versions(self):
        for meson in [
            "project('rhc', version: '0.3.13')",
            "project('rhc', version: '0.3.14')",
            "project('rhc')",
        ]:
            with self.subTest(meson=meson), tempfile.TemporaryDirectory() as temporary:
                output = Path(temporary) / "output"
                matches = "0.3.13" in meson
                expected = (
                    contextlib.nullcontext() if matches else self.assertRaises(SystemExit)
                )
                with (
                    patch.dict(os.environ, {"GITHUB_OUTPUT": str(output)}),
                    patch.object(Path, "read_text", return_value=meson),
                    patch("subprocess.run"),
                    patch(
                        "subprocess.check_output", side_effect=["source-sha\n", "0.3.13\n"]
                    ),
                    expected,
                ):
                    runpy.run_path(str(SCRIPTS / "read-version.py"))
                if matches:
                    self.assertEqual(output.read_text(), "sha=source-sha\nversion=0.3.13\n")
                else:
                    self.assertFalse(output.exists())


if __name__ == "__main__":
    unittest.main()
