"""Read the source version and commit for monthly-build.yml."""

import os
import re
import subprocess
from pathlib import Path

subprocess.run(
    ["git", "config", "--global", "--add", "safe.directory", str(Path.cwd())],
    check=True,
)
sha = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
version = subprocess.check_output(
    ["rpmspec", "--query", "--srpm", "--queryformat", "%{version}\n", "rhc.spec"],
    text=True,
).strip()
meson_version = re.search(
    r"\bversion\s*:\s*['\"]([^'\"]+)['\"]", Path("meson.build").read_text()
)
if meson_version is None or version != meson_version.group(1):
    raise SystemExit("rhc.spec and meson.build must have the same release version")
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
    output.write(f"sha={sha}\nversion={version}\n")
