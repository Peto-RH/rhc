#!/usr/bin/env bash
set -euo pipefail

umask 077
mkdir -p "$HOME/.config"
trap 'rm -f "$HOME/.config/copr"' EXIT
printf '%s\n' "$COPR_CONFIG" > "$HOME/.config/copr"
unset COPR_CONFIG

packit build in-copr --wait --preserve-project \
    --owner "$COPR_OWNER" \
    --project "$COPR_PROJECT" \
    --targets rhel-10-aarch64,rhel-10-x86_64 \
    2>&1 | tee packit-build.log

# Packit's --wait does not fail the command when a remote build fails.
python3 "$(dirname "$0")/check-copr.py" 2>&1 | tee -a packit-build.log
