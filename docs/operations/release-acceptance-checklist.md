# Release acceptance checklist: public-beta first success

Use this checklist only when an owner is preparing a real release. It does not authorize publishing.

- [ ] Owner has selected and recorded the version bump in `pyproject.toml` and `CHANGELOG.md`.
- [ ] Build exactly one wheel and one source distribution from the tagged source.
- [ ] Run the Windows clean-install smoke: `seshat --help`, `init-project`, Git initialization, `status`, `next`, and `check` all pass.
- [ ] Confirm `status` / `next` contain no fabricated pass or numeric score.
- [ ] Confirm the normal install contains no `dev`, `livetest`, database-driver, or file-reader dependency.
- [ ] Verify both `seshat` and legacy `retail` console scripts resolve to `seshat.cli:main`.
- [ ] Verify `python -m seshat.cli check` and legacy `python -m retail.cli check` work.
- [ ] Validate the plugin manifest, its skill, and all `/seshat-*` commands; use the public marketplace flow only after release.
- [ ] Run `seshat check` and `seshat kit-lint` over the release tree.
- [ ] Inspect artifacts and tracked changes for secrets, credentials, hostnames, and machine-specific paths.
- [ ] Confirm upgrade (`pipx upgrade seshat-bi`) and uninstall (`pipx uninstall seshat-bi`) instructions remain accurate.

macOS and Linux smoke coverage is best-effort beta evidence. Windows is the release gate.