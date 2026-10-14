"""Check the remote build submitted by monthly-build.yml."""

import os
import re
from pathlib import Path

from copr.v3 import Client

build_ids = re.findall(
    r"^Build id: ([0-9]+),", Path("packit-build.log").read_text(), re.MULTILINE
)
if len(build_ids) != 1:
    raise SystemExit("Expected one Copr build ID in the Packit output")

client = Client.create_from_config_file()
build_id = int(build_ids[0])
build = client.build_proxy.get(build_id)
build_url = f"{client.config['copr_url'].rstrip('/')}/coprs/build/{build_id}/"
with open(os.environ["GITHUB_OUTPUT"], "a", encoding="utf-8") as output:
    output.write(f"build_url={build_url}\n")
print(f"Copr build: {build_url} ({build.state})")
if build.state != "succeeded":
    raise SystemExit(f"Copr build did not succeed: {build.state}")

for target in ("rhel-10-aarch64", "rhel-10-x86_64"):
    if target not in build.chroots:
        raise SystemExit(f"Copr build is missing target: {target}")
    result = client.build_chroot_proxy.get(build_id, target)
    print(f"{target}: {result.state} ({result.result_url})")
    if result.state != "succeeded":
        raise SystemExit(f"Copr target did not succeed: {target}")
