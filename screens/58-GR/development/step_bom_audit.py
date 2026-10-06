"""Read-only STEP AP214 assembly/BOM inventory; no CAD geometry validation."""

from collections import Counter, defaultdict
from pathlib import Path
import csv
import hashlib
import json
import re
import sys
import unicodedata
import xml.etree.ElementTree as ET
import zipfile


ROOT = Path(r"C:\Users\adm\Downloads\Новая папка")
OUT = Path(__file__).parent
DESIGNATION = re.compile(r"^\d+(?:-\d+)?\.GR\.[\w.-]+", re.I)
REF = re.compile(r"#(\d+)")
X2 = re.compile(r"\\X2\\([0-9A-Fa-f]+)\\X0\\")


def sha256(path):
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def decode_step(s):
    return X2.sub(lambda m: bytes.fromhex(m.group(1)).decode("utf-16-be"), s).replace("''", "'")


def quoted(s):
    m = re.search(r"'((?:''|[^'])*)'", s)
    return decode_step(m.group(1)) if m else ""


def normalize_name(s):
    s = unicodedata.normalize("NFKC", s).upper().replace("Х", "X")
    return re.sub(r"[^A-ZА-ЯЁ0-9]+", "", s)


def entities(path):
    data = path.read_bytes().decode("latin1")
    for m in re.finditer(r"#(\d+)\s*=\s*(.*?);", data, re.S):
        yield int(m.group(1)), m.group(2).strip()


def read_step(path):
    products, formation, definitions, edges = {}, {}, {}, []
    counts = Counter()
    unit_mm = 0
    product_names = []
    for eid, body in entities(path):
        typ = re.match(r"([A-Z_]+)\s*\(", body)
        if typ:
            counts[typ.group(1)] += 1
        if body.startswith("PRODUCT ("):
            products[eid] = quoted(body)
        elif body.startswith("PRODUCT_DEFINITION_FORMATION"):
            refs = REF.findall(body)
            if refs:
                formation[eid] = int(refs[-1])
        elif body.startswith("PRODUCT_DEFINITION ("):
            refs = REF.findall(body)
            if refs:
                definitions[eid] = int(refs[0])
        elif body.startswith("NEXT_ASSEMBLY_USAGE_OCCURRENCE ("):
            refs = REF.findall(body)
            if len(refs) >= 2:
                edges.append((int(refs[0]), int(refs[1])))
        if "LENGTH_UNIT" in body and "SI_UNIT ( .MILLI., .METRE. )" in body:
            unit_mm += 1
    def product_of(def_id):
        return formation.get(definitions.get(def_id))
    product_edges = [(product_of(a), product_of(b)) for a, b in edges]
    used_as_child = {b for _, b in product_edges}
    roots = [i for i in products if i not in used_as_child]
    direct = defaultdict(Counter)
    for a, b in product_edges:
        direct[a][b] += 1
    def descend(node, stack=()):
        if node in stack:
            raise ValueError(f"cycle: {node}")
        if not direct[node]:
            return Counter({node: 1})
        result = Counter()
        for child, qty in direct[node].items():
            for leaf, leaf_qty in descend(child, stack + (node,)).items():
                result[leaf] += qty * leaf_qty
        return result
    leaf_counts = Counter()
    all_counts = Counter()
    def walk(node, multiple=1, stack=()):
        if node in stack:
            raise ValueError(f"cycle: {node}")
        all_counts[node] += multiple
        for child, qty in direct[node].items():
            walk(child, multiple * qty, stack + (node,))
    for root in roots:
        leaf_counts.update(descend(root))
        walk(root)
    for pid, name in products.items():
        d = DESIGNATION.match(name)
        product_names.append({"product_id": pid, "designation": d.group(0) if d else "", "step_name": name,
                              "is_assembly": bool(direct[pid]), "direct_occurrences": sum(direct[pid].values()),
                              "all_occurrences_from_root": all_counts[pid], "leaf_occurrences": leaf_counts[pid]})
    return {
        "filename": path.name, "bytes": path.stat().st_size, "sha256": sha256(path),
        "product_count": len(products), "definition_count": len(definitions),
        "assembly_occurrences": len(edges), "unresolved_edge_refs": sum(a is None or b is None for a,b in product_edges),
        "root_count": len(roots), "roots": [products[i] for i in roots],
        "unique_leaf_products": sum(not direct[i] for i in products),
        "leaf_occurrences_from_roots": sum(leaf_counts.values()),
        "mm_length_unit_declarations": unit_mm,
        "entity_counts": {k: counts[k] for k in ["MANIFOLD_SOLID_BREP", "CLOSED_SHELL", "ADVANCED_FACE", "SHAPE_REPRESENTATION", "PRODUCT", "NEXT_ASSEMBLY_USAGE_OCCURRENCE"]},
        "products": product_names,
    }


def read_bom(path):
    ns = {"x": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        ssroot = ET.fromstring(z.read("xl/sharedStrings.xml"))
        ss = ["".join(x.itertext()) for x in ssroot]
        root = ET.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for r in root.findall(".//x:sheetData/x:row", ns):
        cells = {}
        for c in r.findall("x:c", ns):
            key = re.match(r"[A-Z]+", c.attrib["r"]).group()
            v = c.findtext("x:v", namespaces=ns)
            cells[key] = ss[int(v)] if v is not None and c.attrib.get("t") == "s" else v or ""
        rows.append(cells)
    result = []
    for row in rows[1:]:
        desc = row.get("B", "")
        d = DESIGNATION.match(desc)
        result.append({"position": row.get("A", ""), "designation": d.group(0) if d else "", "bom_name": desc,
                       "material": row.get("C", ""), "quantity": row.get("G", "")})
    return result


def main():
    steps = [p for p in sorted(ROOT.glob("*.STEP")) if " (1).STEP" not in p.name]
    summaries = [read_step(p) for p in steps]
    bom = read_bom(ROOT / "58.GR BOM(6).xlsx")
    bom_by_designation = defaultdict(list)
    for row in bom:
        if row["designation"]:
            bom_by_designation[row["designation"].upper()].append(row)
    for s in summaries:
        with (OUT / ("step_products_" + ("TT" if "ТТ" in s["filename"] else "KT") + ".csv")).open("w", newline="", encoding="utf-8-sig") as f:
            w = csv.DictWriter(f, fieldnames=list(s["products"][0]))
            w.writeheader(); w.writerows(s["products"])
        step_des = {p["designation"].upper() for p in s["products"] if p["designation"]}
        bom_des = set(bom_by_designation)
        s["designation_in_both"] = len(step_des & bom_des)
        s["designation_only_in_step"] = sorted(step_des - bom_des)
        s["designation_only_in_bom"] = sorted(bom_des - step_des)
        s.pop("products")
    kt_path = OUT / "step_products_KT.csv"
    with kt_path.open(encoding="utf-8-sig", newline="") as f:
        kt_products = list(csv.DictReader(f))
    step_by_designation = defaultdict(list)
    step_by_name = defaultdict(list)
    for p in kt_products:
        if p["designation"]:
            step_by_designation[p["designation"].upper()].append(p)
        else:
            step_by_name[normalize_name(p["step_name"])].append(p)
    matrix = []
    for row in bom:
        matches = (step_by_designation.get(row["designation"].upper(), []) if row["designation"]
                   else step_by_name.get(normalize_name(row["bom_name"]), []))
        match_method = "designation" if row["designation"] else "normalized name"
        if len(matches) == 1:
            match_status = "quantity matches" if row["quantity"] == matches[0]["all_occurrences_from_root"] else "quantity differs"
        elif len(matches) > 1:
            match_status = "ambiguous multiple STEP products"
        else:
            match_status = "no match"
        matrix.append({**row, "step_product_count": len(matches),
                       "step_names": " | ".join(x["step_name"] for x in matches),
                       "step_assembly": " | ".join(x["is_assembly"] for x in matches),
                       "step_root_occurrences": " | ".join(x["all_occurrences_from_root"] for x in matches),
                       "match_method": match_method, "match_status": match_status})
    with (OUT / "bom_step_designation_matrix.csv").open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(matrix[0])); w.writeheader(); w.writerows(matrix)
    (OUT / "step_bom_summary.json").write_text(json.dumps({"bom_rows": len(bom), "steps": summaries}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({"bom_rows": len(bom), "steps": [{k:v for k,v in s.items() if not k.startswith("designation_only")} for s in summaries]}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
