#!/usr/bin/env python3
"""Materialize compressed seed/suppression payloads before the crawler runs.

Payload convention:
- seeds/payloads/hotel_seed_domains_*.csv.gz.b64.partNN
- suppression/payloads/suppression_*.csv.gz.b64.partNN

The script concatenates parts by filename order, base64-decodes, gzip-decompresses,
and writes normal CSV files that the crawler can read.
"""

from __future__ import annotations

import base64
import gzip
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def materialize_parts(parts_glob: str, output_path: Path) -> int:
    parts = sorted(ROOT.glob(parts_glob))
    if not parts:
        return 0
    payload = "".join(p.read_text(encoding="utf-8").strip() for p in parts)
    data = gzip.decompress(base64.b64decode(payload))
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_bytes(data)
    return len(parts)


def main() -> int:
    seed_parts = materialize_parts(
        "seeds/payloads/hotel_seed_domains_2026-06-14.csv.gz.b64.part*",
        ROOT / "seeds" / "hotel_seed_domains.csv",
    )
    suppression_parts = materialize_parts(
        "suppression/payloads/suppression_all_emailed_2026-06-14.csv.gz.b64.part*",
        ROOT / "test-runs" / "previous-mails" / "all_emailed_to_date_normalized.csv",
    )
    print(f"Materialized seed payload parts: {seed_parts}")
    print(f"Materialized suppression payload parts: {suppression_parts}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
