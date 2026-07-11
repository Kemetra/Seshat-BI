# Seshat BI readiness review action

This read-only composite integration runs Seshat's existing static gate and retains a
stable review JSON document. It requests no token, posts no PR comment, opens no database,
and cannot grant readiness or approval. Live validation remains explicitly `not_run`.

```yaml
permissions:
  contents: read

steps:
  - uses: actions/checkout@v4 # pin this to a full commit SHA in production
  - uses: ahmed-shaaban-94/Seshat_BI/integrations/github-action@<full-commit-sha>
    with:
      seshat-version: 0.1.0
      commit-range: ${{ github.event.pull_request.base.sha }}..${{ github.sha }}
      sarif: auto
```

Pin both the action reference and `seshat-version` immutably. A range, branch, or `latest`
package selector is refused. The runner needs Python and PowerShell; GitHub-hosted Linux
and Windows runners provide both.

The action writes `.seshat-output/review/seshat-review.json`, a Markdown job summary, and
normally `.seshat-output/review/seshat-results.sarif`. Retained JSON is authoritative when
SARIF is unavailable or an upload policy prevents code-scanning ingestion. Upload SARIF in
a separate workflow step only when `security-events: write` is appropriate; this action's
default permissions remain `contents: read`.

Repeated material results have the same digest, so a wrapper can suppress duplicate
notifications without hiding evidence. This integration deliberately does not post a
comment itself.
