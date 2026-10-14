"""Test release PR creation without contacting GitHub."""

import base64
import contextlib
import io
import json
import os
import runpy
import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SCRIPTS = Path(__file__).parent


class PrepareReleaseTests(unittest.TestCase):
    def test_release_pr(self):
        originals = {
            "rhc.spec": b"Version: 0.3.13\nRelease: %autorelease\n",
            "meson.build": b"project('rhc', version : '0.3.13', meson_version : '>= 0.56.0')\n",
        }
        for case in [
            "success", "invalid-version", "same-version", "invalid-jira",
            "unsigned", "branch-conflict",
        ]:
            with self.subTest(case=case), tempfile.TemporaryDirectory() as temporary:
                summary = Path(temporary) / "summary"
                environment = {
                    "RELEASE_VERSION": "0.3.14",
                    "BASE_BRANCH": "main",
                    "JIRA_ISSUE": "RHEL-1234",
                    "GITHUB_REPOSITORY": "example/rhc",
                    "GITHUB_STEP_SUMMARY": str(summary),
                }
                if case == "invalid-version":
                    environment["RELEASE_VERSION"] = "$(touch unexpected)"
                if case == "same-version":
                    environment["RELEASE_VERSION"] = "0.3.13"
                if case == "invalid-jira":
                    environment["JIRA_ISSUE"] = "invalid"
                response = {
                    "data": {
                        "createCommitOnBranch": {
                            "commit": {"signature": {"isValid": case != "unsigned"}}
                        }
                    }
                }
                expected = (
                    contextlib.nullcontext() if case == "success"
                    else self.assertRaises(
                        subprocess.CalledProcessError if case == "branch-conflict"
                        else SystemExit
                    )
                )
                with (
                    patch.dict(os.environ, environment),
                    patch.object(
                        Path, "read_bytes",
                        side_effect=lambda path: originals[path.name], autospec=True,
                    ),
                    patch.object(Path, "write_bytes") as write,
                    patch("subprocess.run") as create_branch,
                    patch(
                        "subprocess.check_output",
                        side_effect=[
                            "base-sha\n", json.dumps(response),
                            "https://github.com/example/rhc/pull/1\n",
                        ],
                    ) as command,
                    contextlib.redirect_stdout(io.StringIO()),
                    expected,
                ):
                    if case == "branch-conflict":
                        create_branch.side_effect = subprocess.CalledProcessError(1, "gh")
                    runpy.run_path(str(SCRIPTS / "prepare-release.py"), run_name="__main__")
                write.assert_not_called()
                if case == "success":
                    request = json.loads(command.call_args_list[1].kwargs["input"])[
                        "variables"
                    ]["input"]
                    self.assertEqual(request["expectedHeadOid"], "base-sha")
                    self.assertEqual(request["branch"]["branchName"], "release-v0.3.14")
                    self.assertEqual(
                        request["message"]["headline"], "chore: Release rhc-v0.3.14"
                    )
                    for addition in request["fileChanges"]["additions"]:
                        self.assertEqual(
                            base64.b64decode(addition["contents"]),
                            originals[addition["path"]].replace(b"0.3.13", b"0.3.14"),
                        )
                    self.assertIn("https://github.com/example/rhc/pull/1", summary.read_text())
                elif case == "unsigned":
                    self.assertEqual(command.call_count, 2)
                else:
                    self.assertFalse(summary.exists())


if __name__ == "__main__":
    unittest.main()
