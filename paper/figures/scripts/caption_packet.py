"""Assemble current figure captions/Descriptions and 27 table captions, no TeX."""

if not __debug__:
    raise SystemExit("Optimized Python is unsupported: verification must remain enabled.")

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORDER = [("1", "f01_obligations"), ("2", "f02_local_lowering"), ("3", "f07_confirmation"),
         ("4", "f04_few_column"), ("5", "f05_prefill"), ("6", "f06_b570"),
         ("S1", "f03_transaction"), ("S2", "f08_c4_initial")]
ALT = ["f02_layered", "f03_alternate", "f05_prompt_length"]


def main():
    caps = {}
    for d in ("method", "results", "tail"):
        caps.update(json.loads((ROOT / d / "captions.json").read_text()))
    caps.update(json.loads((ROOT / "captions" / "alternatives.json").read_text()))
    lines = ["# 已整合的图注与 Description 清单", "",
             "本文件覆盖8张正式图、3个未编号备选与27张表，共38项；由当前caption源生成。Description说明视觉关系，不代表人类无障碍测试或认证。完整论文及页面验收位于父级交付，不由旧#276机械预览代替。", ""]
    for ident, stem in ORDER:
        c = caps[stem]
        lines += [f"## Figure {ident} · {stem}", "", f"**Caption.** {c['caption']}", "",
                  f"**Accessible description.** {c['description']}", ""]
    lines += ["## Alternative layouts", ""]
    for stem in ALT:
        c = caps[stem]
        lines += [f"### {stem}", "", f"**Caption.** {c['caption']}", "",
                  f"**Accessible description.** {c['description']}", ""]
    lines += ["## Table captions", ""]
    tabs = json.loads((ROOT / "table_design" / "captions.json").read_text())
    inv = json.loads((ROOT / "provenance" / "EXHIBIT_INVENTORY.json").read_text())
    for key, value in inv.items():
        if value["kind"] == "table":
            lines += [f"- **Table {value['id']}** (`{key}`): {tabs[key]}"]
    out = ROOT / "proof" / "FIGURE_CAPTION_PACKET.md"
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    print("caption packet:", len(lines), "lines")


if __name__ == "__main__":
    main()
