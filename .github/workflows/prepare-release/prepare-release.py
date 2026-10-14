"""Create the version bump PR for prepare-release.yml."""

import base64
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


def main():
    version = os.environ["RELEASE_VERSION"]
    jira_issue = os.environ["JIRA_ISSUE"]
    repository = os.environ["GITHUB_REPOSITORY"]
    base_branch = os.environ["BASE_BRANCH"]
    version_pattern = r"[0-9]+\.[0-9]+\.[0-9]+"
    if not re.fullmatch(version_pattern, version):
        raise SystemExit("release_version must be X.Y.Z, for example 0.3.14")
    if not re.fullmatch(r"(CCT|RHEL)-[1-9][0-9]*", jira_issue):
        raise SystemExit("jira_issue must be a CCT or RHEL card, for example CCT-1234")

    additions = []
    versions = []
    for path, pattern in (
        ("rhc.spec", r"^Version:[ \t]+([^ \t\r\n]+)[ \t]*\r?$"),
        ("meson.build", r"\bproject\(\s*'rhc',\s*version\s*:\s*'([^']+)'"),
    ):
        contents = Path(path).read_bytes().decode("utf-8")
        matches = list(re.finditer(pattern, contents, re.MULTILINE))
        if len(matches) != 1 or not re.fullmatch(version_pattern, matches[0].group(1)):
            raise SystemExit(f"Expected one X.Y.Z release version in {path}")
        match = matches[0]
        versions.append(match.group(1))
        contents = contents[: match.start(1)] + version + contents[match.end(1) :]
        additions.append(
            {"path": path, "contents": base64.b64encode(contents.encode("utf-8")).decode()}
        )

    if versions[0] != versions[1]:
        raise SystemExit("rhc.spec and meson.build must have the same release version")
    if tuple(map(int, version.split("."))) <= tuple(map(int, versions[0].split("."))):
        raise SystemExit("release_version must be newer than the current version")

    head = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
    branch = f"release-v{version}"
    title = f"chore: Release rhc-v{version}"
    subprocess.run(
        ["gh", "api", f"repos/{repository}/git/refs", "--method", "POST", "--input", "-"],
        input=json.dumps({"ref": f"refs/heads/{branch}", "sha": head}),
        text=True,
        check=True,
    )

    # This API creates a GitHub-signed commit without storing a signing key.
    query = """
        mutation($input: CreateCommitOnBranchInput!) {
            createCommitOnBranch(input: $input) {
                commit { signature { isValid } }
            }
        }
    """
    commit_input = {
        "branch": {"repositoryNameWithOwner": repository, "branchName": branch},
        "expectedHeadOid": head,
        "message": {
            "headline": title,
            "body": f"Bump the upstream release version to {version}.\n\n* Card ID: {jira_issue}",
        },
        "fileChanges": {"additions": additions},
    }
    response = subprocess.check_output(
        ["gh", "api", "graphql", "--input", "-"],
        input=json.dumps({"query": query, "variables": {"input": commit_input}}),
        text=True,
    )
    signature = json.loads(response)["data"]["createCommitOnBranch"]["commit"]["signature"]
    if not signature or not signature["isValid"]:
        raise SystemExit("GitHub did not create a valid signed commit; no PR was opened")

    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8") as body:
        body.write(
            f"Bump `rhc.spec` and `meson.build` from {versions[0]} to {version}.\n\n"
            f"* Card ID: {jira_issue}\n\n"
            "Review and merge this PR manually.\n"
        )
        body.flush()
        pr_url = subprocess.check_output(
            [
                "gh", "pr", "create", "--repo", repository,
                "--base", base_branch, "--head", branch,
                "--title", title, "--body-file", body.name,
            ],
            text=True,
        ).strip()
    print(pr_url)
    with open(os.environ["GITHUB_STEP_SUMMARY"], "a", encoding="utf-8") as summary:
        summary.write(f"Version bump PR: {pr_url}\n")


if __name__ == "__main__":
    main()
