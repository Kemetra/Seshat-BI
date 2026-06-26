# Visual Identity -- Seshat BI

- **Status:** Active -- the committed brand for the product.
- **Product:** Seshat BI (package alias `Seshat_BI`; previously developed under the internal name *Tower BI Agent Kit*).
- **Operating spine:** the **Readiness System** (Source -> Mapping -> Silver -> Gold -> Semantic Model -> Dashboard -> Publish).
- **Use for:** README visuals, docs covers, Power BI theme direction, dashboard headers, CLI/app icon experiments, portfolio presentation.

Seshat BI is the visual identity for an agent-first Retail BI readiness system that turns messy retail data into trusted, governed BI.

The identity should feel like:

```text
ancient knowledge + governed analytics + modern BI engineering
```

---

## 1. Names

| Name | Role |
|------|------|
| **Seshat BI** | The product -- its public name, repo, CLI package (`Seshat_BI`), and brand. Use it everywhere. |
| **Readiness System** | The governance spine inside the product: Source -> Mapping -> Silver -> Gold -> Semantic Model -> Dashboard -> Publish. |
| **Tower BI Agent Kit** | *Historical.* The former internal development name for the same product. Kept only to explain older references; do not use it for new material. |

Use **Seshat BI** in all current material -- developer docs, agent contracts,
README, portfolio, covers, and Power BI theming alike. The only time
*Tower BI Agent Kit* appears is when a doc explains the rename for readers who
knew the old name.

---

## 2. Core symbol

The identity is built around Seshat, the ancient Egyptian figure associated with writing, measurement, record keeping, and knowledge.

The modern BI interpretation:

| Ancient cue | BI interpretation |
|-------------|-------------------|
| Seshat figure | governed knowledge, documentation, auditability |
| Seven-point Seshat star | canonical truth, navigation, measured structure |
| Reed/stylus | source mapping and documentation before transformation |
| Hieroglyphic line art | historical depth, disciplined record keeping |
| Teal data network | modern data lineage, BI model, agent workflow |
| Gold orbit/ring | governance gates and readiness stages |

---

## 3. Non-negotiable brand rules

1. The Seshat star must be **seven-pointed**, not eight-pointed.
2. Do not use compass stars, generic north stars, or eight-ray asterisks as substitutes.
3. The Egyptian figure must look like clean Egyptian-inspired line art, not a random cartoon or fantasy icon.
4. The figure should hold a stylus or writing instrument to reinforce mapping/documentation.
5. Teal data nodes should represent data lineage or semantic connections, not decorative bubbles.
6. Power BI visuals must stay readable and professional; the Egyptian motif is a brand accent, not dashboard clutter.
7. Never let visual polish override readiness gates, metric contracts, or validation evidence.

---

## 4. Logo system

Recommended logo family:

| Asset | Purpose |
|-------|---------|
| Primary logo | Seshat figure + seven-point star + data network + `SESHAT BI` wordmark. |
| Wordmark | Compact horizontal logo for README/docs headers. |
| Stacked logo | Cover pages, portfolio slides, dashboard title pages. |
| CLI/app icon | Seven-point star inside navy rounded square, with gold orbit and teal node path. |
| Hieroglyphic signature | Seven-point star + bowl glyph + seated writing Seshat + `Seshat` wordmark. |
| Monochrome dark | Navy-only usage on light backgrounds. |
| Monochrome gold | Gold-only usage on navy backgrounds. |

Minimum safe rule: if the logo appears small, use the CLI/app icon or simple seven-point star. Do not shrink the full goddess illustration until it becomes unreadable.

---

## 5. Color palette

| Token | Hex | Use |
|-------|-----|-----|
| `deep_navy` | `#001E35` | Main background, text, premium technical base. |
| `midnight_navy` | `#04172A` | Dark surfaces, app icon background. |
| `rich_gold` | `#C69214` | Star, rings, dividers, premium highlights. |
| `gold_light` | `#F2C14E` | Small highlights and metallic gradients. |
| `teal` | `#0B9A9A` | BI/data network, `BI` accent, active states. |
| `teal_light` | `#31C6C2` | Node highlights and hover states. |
| `ivory` | `#F7F1E7` | Brand board background, docs covers. |
| `sand` | `#E8D8BD` | Subtle separators, soft panels. |

Color usage ratio:

```text
60% ivory / navy base
25% deep navy text and structure
10% rich gold premium accents
5% teal data accents
```

---

## 6. Typography direction

Use font stacks, not committed font binaries.

| Use | Direction | Suggested stack |
|-----|-----------|-----------------|
| Logo wordmark | Elegant high-contrast serif | `Cinzel`, `Cormorant Garamond`, `Georgia`, serif |
| Product headings | Modern technical sans | `Inter`, `Segoe UI`, `Arial`, sans-serif |
| Body/docs | Highly readable sans | `Inter`, `Segoe UI`, `Arial`, sans-serif |
| Code/CLI | Monospace | `JetBrains Mono`, `Cascadia Code`, `Consolas`, monospace |

Use wide letter spacing for labels such as `PRIMARY LOGO`, `READINESS SYSTEM`, and `RETAIL BI`.

---

## 7. Dashboard styling principles

Seshat BI dashboards should look premium, but the priority is trust.

Rules:

- Use navy and ivory backgrounds, not loud gradients.
- Use gold sparingly for section dividers, KPI accents, and active focus.
- Use teal for data lineage, selected states, or BI-specific accents.
- Do not decorate every visual with Egyptian motifs.
- Reserve the Seshat symbol for cover/header/control-room pages.
- Every KPI card must trace back to a metric contract.
- Every executive page should have a clear date context and comparison period.

---

## 8. README and docs usage

Recommended placements:

| Place | Visual treatment |
|-------|------------------|
| README top | Small wordmark or simple seven-point star badge. |
| Architecture docs | Minimal Seshat BI badge, then technical diagrams. |
| Readiness docs | Gold seven-stage orbit motif can be used as a subtle metaphor. |
| Worked examples | Keep visuals minimal; prioritize source-map evidence. |
| Power BI docs | Use dashboard theme tokens and control-room page style. |
| Portfolio export | Use the full primary identity board or stacked logo. |

---

## 9. Asset governance

Store final brand assets under:

```text
assets/brand/
```

Suggested files:

```text
assets/brand/seshat-seven-star.svg
assets/brand/seshat-cli-icon.svg
assets/brand/seshat-wordmark.svg
assets/brand/seshat-brand-board.png
assets/brand/seshat-palette.json
```

Only commit assets that are stable enough to reuse. Draft generations can live outside the repo until approved.

---

## 10. Current asset decision

The current visual direction is approved conceptually with one correction requirement:

```text
All stars/emblems must be seven-pointed.
All hieroglyphic/Seshat figures must be cleaned toward a historically coherent seated/writing form.
```

Before using the identity in a production README, portfolio, or Power BI theme, export a clean final asset set and verify the seven-point star in every logo variant.
