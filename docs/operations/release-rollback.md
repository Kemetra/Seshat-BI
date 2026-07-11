# Release rollback

Publication remains an owner action. If a published public-beta artifact is defective, preserve truthful status while recovering:

1. **Package:** yank or withdraw the broken `seshat-bi` release from the package index, revert to the prior known-good tagged source, and publish a corrected owner-approved version when ready. Do not claim the withdrawn version is usable.
2. **Plugin:** revert the repository-root marketplace manifest and plugin source to the prior released tag or commit. If a future generated mirror is ever adopted, regenerate it one way from the corrected canonical source; never repair it by hand.
3. **Status:** downgrade public wording to draft or beta until the corrected artifact is available. Update the changelog and release notes with the withdrawal and recovery facts.
4. **Verification:** repeat the release acceptance checklist, including the Windows clean-install smoke, before any replacement release.

No rollback procedure authorizes disclosure of credentials or machine-specific paths.