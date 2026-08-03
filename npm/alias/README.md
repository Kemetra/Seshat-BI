# seshat-bi

**This is an alias.** The real package is
[`@kemetra/seshat-bi`](https://www.npmjs.com/package/@kemetra/seshat-bi) — the
Seshat BI agent skills bundle for Claude Code. This package holds the unscoped
name and re-exports the scoped one, so both resolve to the same content.

**Prefer installing the scoped package directly:**

```sh
npm install @kemetra/seshat-bi
```

Installing `seshat-bi` works and re-exports everything, but adds one level of
indirection for no benefit.

## Two different things share this name

| Name | Registry | What it is |
|---|---|---|
| `seshat-bi` | **npm** | this alias → the agent skills bundle (content only) |
| `seshat-bi` | **PyPI** | the actual Seshat BI **CLI**, a Python program |

They are different artifacts that happen to share a string. **npm cannot
install the CLI.** If you want the `seshat` command:

```sh
pipx install "seshat-bi[mcp]"
```

## What the real package contains

21 agent skills, the `/seshat-bi:*` slash commands, and reviewed public
Knowledge Bases for Claude Code — Markdown, JSON, and YAML. Zero dependencies,
no install scripts, executes nothing.

For most people npm is **not** the right install path. Use the Claude Code
marketplace, which self-updates:

```
/plugin marketplace add Kemetra/Seshat-BI
/plugin install seshat-bi@seshat-bi-marketplace
```

See the [scoped package README](https://www.npmjs.com/package/@kemetra/seshat-bi)
for full detail.

Apache-2.0 © Ahmed Shaaban
