from pathlib import Path
import re

path = Path(r"C:\Users\adm\Documents\Codex\2026-10-03\new-chat\outputs\Песколовка\GRIT_CHAMBER_CODEX_TASK.md")
text = path.read_text(encoding="utf-8")

for number, name in enumerate(["BASE_700x900", "NARROW_600x1050", "SHORT_WIDE_800x800"], start=49):
    heading = f"# {number}. CFD RECORD — {name}"
    start = text.index(heading)
    end = text.index("\n---", start)
    block = text[start:end]
    block = block.replace("`STATUS = NOT_RUN`", "`STATUS = NOT_RUN_CAPABILITY_GAP`", 1)
    block = re.sub(r"`([A-Z][A-Z0-9_]*) =`", r"`\1 = NOT_AVAILABLE_NO_CFD_RUN`", block)
    text = text[:start] + block + text[end:]

comparison = """| Parameter | BASE | NARROW | SHORT_WIDE |
|---|---:|---:|---:|
| A_settle, m2 | 0.630 analytical | 0.630 analytical | 0.640 analytical |
| V, m3 | 0.3465 analytical | 0.3465 analytical | 0.3520 analytical |
| T theoretical, s | 57.75 | 57.75 | 58.67 |
| Q/A, m/s | 0.009524 | 0.009524 | 0.009375 |
| Vavg settling zone, m/s | 0.01558 analytical | 0.01818 analytical | 0.01364 analytical |
| Vmax bottom | NOT_RUN | NOT_RUN | NOT_RUN |
| Max water level | NOT_RUN | NOT_RUN | NOT_RUN |
| Min freeboard | NOT_RUN | NOT_RUN | NOT_RUN |
| Pressure loss | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.10 | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.15 | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.20 | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.30 | NOT_RUN | NOT_RUN | NOT_RUN |
| eta 0.50 | NOT_RUN | NOT_RUN | NOT_RUN |
| Short circuit | NOT_RUN | NOT_RUN | NOT_RUN |
| Mesh convergence | NOT_RUN | NOT_RUN | NOT_RUN |
| Mass balance | NOT_RUN | NOT_RUN | NOT_RUN |"""
start = text.index("| Parameter | BASE | NARROW | SHORT_WIDE |")
end = text.index("\n---", start)
text = text[:start] + comparison + "\n" + text[end:]

path.write_text(text, encoding="utf-8")
