"""Design tokens for the status dashboard as one inline CSS string.

Ported from the "Seshat BI — Control Center" handoff (colors_and_type.css +
the prototype's inline shell styles). No @import, no web fonts (fallback
stacks only), no remote asset — the output HTML must be self-contained.
"""

from __future__ import annotations

DASHBOARD_CSS: str = """
* { box-sizing: border-box; }
html, body { margin: 0; padding: 0; }
body {
  font-family: 'Segoe UI', Tahoma, system-ui, 'Inter', sans-serif;
  background: #F4F6F9; color: #1B2A3A;
}
.app { display: flex; min-height: 100vh; }
.sidebar {
  width: 224px; flex: none; background: #001E35; color: #F7F1E7;
  position: sticky; top: 0; height: 100vh; padding: 22px 16px;
}
.brand { font-size: 21px; font-weight: 700; letter-spacing: .06em; }
.brand small { display: block; font-size: 11px; color: #9FB2C4; font-weight: 500; }
.nav a {
  display: block; color: #A9BACB; text-decoration: none; padding: 12px 14px;
  border-radius: 11px; font-size: 14.5px; margin-top: 4px;
}
.nav a:hover { color: #F7F1E7; }
main { flex: 1; min-width: 0; padding: 24px 34px 48px; overflow: auto; }
h1 { font-size: 25px; font-weight: 700; color: #0F2033; margin: 0 0 4px; }
.sub { color: #64748B; font-size: 13px; margin: 0 0 22px; }
.kpis { display: grid; grid-template-columns: repeat(4, 1fr); gap: 20px; margin-bottom: 22px; }
.card {
  background: #fff; border: 1px solid #EAEEF3; border-radius: 16px;
  padding: 22px 24px; box-shadow: 0 1px 2px rgba(16,32,51,.04);
}
.kpi .label { font-size: 14px; color: #64748B; font-weight: 600; }
.kpi .value { font-size: 40px; font-weight: 800; color: #0F2033; line-height: 1; margin-top: 6px; }
table { width: 100%; border-collapse: collapse; }
th, td { text-align: right; padding: 12px 16px; font-size: 13px; }
th { background: #F8FAFC; color: #64748B; font-weight: 600; font-size: 12.5px; }
td { border-top: 1px solid #EEF1F5; color: #334155; }
.chip { display: inline-block; padding: 4px 12px; border-radius: 999px; font-size: 12px; font-weight: 700; }
.dot { display: inline-block; width: 12px; height: 12px; border-radius: 50%; margin: 0 2px; }
.stepper { display: flex; gap: 8px; flex-wrap: wrap; margin: 12px 0; }
.stage {
  flex: 1 1 120px; text-align: center; padding: 10px 8px; border-radius: 12px;
  font-size: 12.5px; font-weight: 600;
}
.evidence { margin: 6px 0 0; padding-inline-start: 18px; color: #475569; font-size: 12.5px; }
.blocker {
  background: #FDECEC; color: #C0392B; border-radius: 10px; padding: 10px 14px;
  font-size: 12.5px; margin-top: 8px;
}
.next { color: #0F2033; font-weight: 600; margin-top: 10px; }
a.tealref { color: #0C7C7A; text-decoration: none; }
.empty { padding: 60px; text-align: center; color: #64748B; font-size: 15px; }
.meta { color: #64748B; font-size: 12.5px; margin-bottom: 14px; }
.metarow { color: #64748B; font-size: 12.5px; margin: 0 0 18px; }
.banner {
  background: #E6F2F1; color: #0C7C7A; border: 1px solid #B7DEDC;
  border-radius: 12px; padding: 14px 18px; font-size: 13px; font-weight: 600;
  margin: 22px 0 4px; line-height: 1.6;
}
.icon { width: 15px; height: 15px; vertical-align: -2px; }
.nav a .icon { margin-inline-end: 8px; }
.dotsvg { vertical-align: middle; margin: 0 2px; }
"""
