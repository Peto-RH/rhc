# Monthly RHEL builds

Follow [Prepare upstream release](PREPARE_RELEASE.md) to open and merge
an upstream version bump PR. Then use
[Monthly RHEL upstream build](../.github/workflows/monthly-build.yml) to create
source/vendor tarballs and build RHEL 10 RPMs with Packit/Copr.

## Setup

Add these in **Settings > Secrets and variables > Actions**:

| Setting | Kind | Value |
| --- | --- | --- |
| `COPR_OWNER` | Variable | Copr username or `@group` |
| `COPR_PROJECT` | Variable | Copr project name |
| `COPR_CONFIG` | Secret | Full `[copr-cli]` config from your Copr API page ([Fedora Copr example](https://copr.fedorainfracloud.org/api/)) |

Use a separate Copr project with only `rhel-10-aarch64` and `rhel-10-x86_64`
enabled. The account needs owner/admin permissions because Packit can update
project settings. The workflow must be on the default branch, and you need
repository write access to run it.

## Build the release

Check out the merged release commit, then create and push its annotated tag:

```shell
git tag -m vX.Y.Z vX.Y.Z
git push origin vX.Y.Z
```

1. Open **Actions > Monthly RHEL upstream build > Run workflow**.
2. Select `main` as the workflow branch.
3. Set `build_ref` to the release tag and click **Run workflow**. Branch names
   also work for test builds.

Or use GitHub CLI:

```shell
gh workflow run monthly-build.yml --ref main -f build_ref=vX.Y.Z
gh run watch
```

The selected branch or tag needs `Makefile`, `.packit.yaml`, `rhc.spec`, and
`meson.build`.

The summary shows the version, commit SHA, Copr link, and result. Both RHEL
targets must succeed. Copr has the RPMs and build logs. Download and unzip the
`monthly-rhel-sources-*` artifact for `rhc-VERSION.tar.gz` and
`rhc-VERSION-vendor.tar.bz2`. Artifacts are kept for 30 days.

Create a draft GitHub release from the tag, attach `rhc-VERSION.tar.gz`, and
publish it manually. Keep the vendor tarball for downstream packaging.

## Downstream builds

Use the published upstream version and its matching vendor tarball. Use
`rhpkg` for RHEL or `centpkg` for CentOS Stream. You need package access and
an active Red Hat Kerberos ticket.

1. Check out the target release branch and create a working branch. Check that
   the Jira ticket's **Fix Version/s** matches the target release.
2. Update the downstream spec for the released version.
3. Download the source files listed in that spec with `spectool -g rhc.spec`.
   Set `VERSION` to the release version and upload both tarballs together:

   ```shell
   rhpkg new-sources "rhc-$VERSION.tar.gz" "rhc-$VERSION-vendor.tar.bz2"
   ```

   Use `centpkg new-sources` for CentOS Stream. Include any other source archives
   required by the spec: `new-sources` replaces the old source list.
4. Commit the packaging changes with `- Resolves: RHEL-...` in the message.
   Push your branch and open a GitLab merge request.
5. Check the MR build and tests, then use the project's merge process.

For legacy RHEL dist-git, push the packaging commit and run `rhpkg build`.
