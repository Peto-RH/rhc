# Prepare an upstream release PR

Use [Prepare upstream release](../.github/workflows/prepare-release.yml) to
open a version bump PR. You review and merge it manually.

## Setup

In **Settings > Actions > General**, enable **Allow GitHub Actions to create
and approve pull requests**. No extra secret is needed: the workflow uses
GitHub's built-in token and creates a GitHub-signed commit.

The workflow must be on the default branch. You need repository write access
to run it.

## Run it

1. Merge pending translation PRs.
2. Open **Actions > Prepare upstream release > Run workflow**.
3. Select the workflow branch. Enter `release_version` (for example `0.3.14`),
   `base_branch` (usually `main`), and the owning team's `jira_issue`
   (such as `CCT-1234` or `RHEL-1234`).
4. Open the PR linked in the run summary. It changes only the version in
   `rhc.spec` and `meson.build`.
5. If GitHub shows **Approve workflows to run**, click it to start the PR checks.
6. Review and merge the PR manually.

Both files must have the same current version. The new version must be higher.
The workflow creates `release-vVERSION`; if that branch already exists, it
stops without replacing it. Inspect the branch before retrying.

## Test before merging this workflow

Push the implementation to your own fork (a GitHub copy of the repository).
Enable Actions and make the implementation branch the fork's default branch.
Enable PR creation as described above.

Run the workflow with `base_branch` set to that implementation branch and
a higher version. Check that the PR stays in your fork, changes only the two
version values, and contains a **Verified** signed commit. No release tag
or publication is required for this test.
