#!/usr/bin/env bash
set -euo pipefail

{
    printf '## Monthly RHEL upstream build\n\n'
    printf -- '- Requested ref: %s\n' "$BUILD_REF"
    printf -- '- Source commit: %s\n' "$SOURCE_SHA"
    printf -- '- Version: %s\n' "$VERSION"
    printf -- '- Copr project: %s/%s\n' "$COPR_OWNER" "$COPR_PROJECT"
    printf -- '- Copr build: %s\n' "$COPR_BUILD_URL"
    printf -- '- Targets: rhel-10-aarch64, rhel-10-x86_64\n'
    printf -- '- Packit build result: %s\n' "$BUILD_RESULT"
    printf -- '- Workflow result: %s\n' "$WORKFLOW_RESULT"
    printf '\nDownload the source and vendor tarballs from the source artifact.\n'
    printf 'See the Packit build log for the Copr build URL, per-target results, and RPMs.\n'
} >> "$GITHUB_STEP_SUMMARY"
