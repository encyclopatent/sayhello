#!/usr/bin/env python3
import argparse, csv, json, re, shutil, subprocess, textwrap
from pathlib import Path

FIELDS = [
    "qseqid", "sseqid", "pident", "length", "mismatch", "gapopen",
    "qstart", "qend", "sstart", "send", "evalue", "bitscore",
    "qcovs", "saccver", "stitle"
]

PATTERNS = [
    re.compile(r"\b(WO)\s*(\d{4})\s*/?\s*(\d{4,7})\s*([A-Z]\d?)?\b", re.I),
    re.compile(r"\b(US|EP|CN|JP|KR|IN|AU|CA|BR|MX|TW|PH|TH|VN|MY|ID|UY|GB|DE|FR|ES|IT|NL|DK|FI|NO|SE|RU)\s*[- ]?\s*(\d{5,12})\s*([A-Z]\d?)?\b", re.I),
]

def normalize_patent(m):
    groups = m.groups()
    cc = groups[0].upper()
    if cc == "WO":
        kind = (groups[3] or "").upper()
        return f"WO{groups[1]}{groups[2]}{kind}"
    kind = (groups[2] or "").upper()
    return f"{cc}{groups[1]}{kind}"

def extract_patents(text):
    found = []
    for pat in PATTERNS:
        for m in pat.finditer(text or ""):
            found.append(normalize_patent(m))
    return sorted(set(found))

def write_query(outdir, sequence=None, fasta=None):
    outdir.mkdir(parents=True, exist_ok=True)
    q = outdir / "query.fasta"
    if fasta:
        q.write_text(Path(fasta).read_text(), encoding="utf-8")
    else:
        seq = re.sub(r"\s+", "", sequence or "")
        q.write_text(">query\n" + "\n".join(textwrap.wrap(seq, 80)) + "\n", encoding="utf-8")
    return q

def run_blast(program, db, query, out_tsv, max_targets, evalue):
    exe = shutil.which(program)
    if not exe:
        raise SystemExit(f"{program} not found. Please install NCBI BLAST+ first.")
    outfmt = "6 " + " ".join(FIELDS)
    cmd = [
        exe, "-remote",
        "-db", db,
        "-query", str(query),
        "-evalue", str(evalue),
        "-max_target_seqs", str(max_targets),
        "-outfmt", outfmt,
        "-out", str(out_tsv),
    ]
    subprocess.run(cmd, check=True)

def parse_hits(raw_tsv, min_identity=0, min_qcov=0):
    best = {}
    all_rows = []
    with open(raw_tsv, newline="", encoding="utf-8", errors="replace") as f:
        reader = csv.DictReader(f, fieldnames=FIELDS, delimiter="\t")
        for row in reader:
            if not row.get("pident"):
                continue
            pident = float(row["pident"])
            qcovs = float(row.get("qcovs") or 0)
            bitscore = float(row.get("bitscore") or 0)
            if pident < min_identity or qcovs < min_qcov:
                continue

            text = " ".join([row.get("sseqid", ""), row.get("saccver", ""), row.get("stitle", "")])
            patents = extract_patents(text)
            row["patents"] = patents
            all_rows.append(row)

            for pn in patents:
                old = best.get(pn)
                if old is None or bitscore > float(old.get("bitscore") or 0):
                    best[pn] = row

    return all_rows, best

def write_outputs(outdir, all_rows, best):
    best_tsv = outdir / "patents_best_hits.tsv"
    best_json = outdir / "patents_best_hits.json"
    summary = outdir / "summary.md"

    cols = ["patent"] + FIELDS
    with open(best_tsv, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=cols, delimiter="\t")
        w.writeheader()
        for patent, row in sorted(best.items()):
            w.writerow({"patent": patent, **{k: row.get(k, "") for k in FIELDS}})

    data = [{"patent": p, **{k: r.get(k, "") for k in FIELDS}} for p, r in sorted(best.items())]
    best_json.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")

    lines = [
        "# NCBI Patent Sequence Search Summary",
        "",
        f"- Filtered BLAST hits: {len(all_rows)}",
        f"- Deduplicated patent numbers: {len(best)}",
        "",
        "| Patent | Identity | Qcov | E-value | Bitscore | Accession | Title |",
        "|---|---:|---:|---:|---:|---|---|",
    ]
    for patent, row in sorted(best.items(), key=lambda x: -float(x[1].get("bitscore") or 0))[:50]:
        lines.append(
            f"| {patent} | {row.get('pident')} | {row.get('qcovs')} | "
            f"{row.get('evalue')} | {row.get('bitscore')} | {row.get('saccver')} | "
            f"{(row.get('stitle') or '')[:120]} |"
        )
    summary.write_text("\n".join(lines) + "\n", encoding="utf-8")

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--sequence")
    ap.add_argument("--fasta")
    ap.add_argument("--parse-tsv")
    ap.add_argument("--program", default="blastp")
    ap.add_argument("--db", default="pataa")
    ap.add_argument("--min-identity", type=float, default=0)
    ap.add_argument("--min-qcov", type=float, default=0)
    ap.add_argument("--max-targets", type=int, default=500)
    ap.add_argument("--evalue", default="1e-5")
    ap.add_argument("--outdir", default="ncbi_patent_results")
    args = ap.parse_args()

    outdir = Path(args.outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    raw = outdir / "raw_hits.tsv"

    if args.parse_tsv:
        raw = Path(args.parse_tsv)
    else:
        query = write_query(outdir, sequence=args.sequence, fasta=args.fasta)
        run_blast(args.program, args.db, query, raw, args.max_targets, args.evalue)

    all_rows, best = parse_hits(raw, args.min_identity, args.min_qcov)
    write_outputs(outdir, all_rows, best)
    print(f"Done. Results written to: {outdir}")

if __name__ == "__main__":
    main()
