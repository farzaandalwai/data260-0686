import csv
import hashlib
import io
import json
import zipfile
from collections import defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

import requests


DATA_URL = "https://divvy-tripdata.s3.amazonaws.com/202601-divvy-tripdata.zip"
PRICE_URL = "https://divvybikes.com/pricing"
RAW = Path("reports/hw07/raw")
FIELDS = ["ride_id", "rideable_type", "started_at", "ended_at", "duration_minutes", "week", "scenario_selected"]


class PageText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style"):
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in ("script", "style") and self.hidden:
            self.hidden -= 1

    def handle_data(self, data):
        value = " ".join(data.split())
        if value and not self.hidden:
            self.parts.append(value)


def fetch_source():
    response = requests.get(DATA_URL, timeout=120)
    response.raise_for_status()
    archive = response.content
    sha = hashlib.sha256(archive).hexdigest()
    grouped = defaultdict(list)
    with zipfile.ZipFile(io.BytesIO(archive)) as folder:
        csv_name = next(name for name in folder.namelist() if name.endswith(".csv"))
        with folder.open(csv_name) as file:
            reader = csv.DictReader(io.TextIOWrapper(file, encoding="utf-8-sig"))
            for row in reader:
                if row["rideable_type"] != "classic_bike":
                    continue
                try:
                    start = datetime.fromisoformat(row["started_at"])
                    end = datetime.fromisoformat(row["ended_at"])
                except ValueError:
                    continue
                minutes = (end - start).total_seconds() / 60
                if not 1 <= minutes <= 45:
                    continue
                week = min((start.day - 1) // 7 + 1, 4)
                if len(grouped[week]) < 260:
                    grouped[week].append({
                        "ride_id": row["ride_id"],
                        "rideable_type": row["rideable_type"],
                        "started_at": row["started_at"],
                        "ended_at": row["ended_at"],
                        "duration_minutes": round(minutes, 2),
                        "week": week,
                    })
                if all(len(grouped[number]) >= 250 for number in range(1, 5)):
                    break
    if not all(len(grouped[number]) >= 250 for number in range(1, 5)):
        raise RuntimeError("Official source did not provide enough classic-bike rows")
    return grouped, sha


def write_scenario(name, grouped, start_index, selected_per_week):
    rows = []
    for week in range(1, 5):
        chosen = grouped[week][start_index:start_index + 125]
        for index, row in enumerate(chosen):
            rows.append({**row, "scenario_selected": int(index < selected_per_week[week - 1])})
    with (RAW / f"divvy_{name}.csv").open("w", newline="") as file:
        writer = csv.DictWriter(file, FIELDS)
        writer.writeheader()
        writer.writerows(rows)
    return {"rows": len(rows), "attributed_rides": sum(row["scenario_selected"] for row in rows)}


def save_pricing():
    response = requests.get(PRICE_URL, timeout=30)
    response.raise_for_status()
    raw = response.content
    (RAW / "divvy_pricing.html").write_bytes(raw)
    parser = PageText()
    parser.feed(response.text)
    text = "\n".join(parser.parts)
    (RAW / "divvy_pricing.txt").write_text(text)
    if "$143.90/year" not in text or "$1 + $0.20/min" not in text:
        raise RuntimeError("Official pricing text changed; review rates before analysis")
    return {
        "url": PRICE_URL,
        "accessed_utc": datetime.now(timezone.utc).isoformat(),
        "html_sha256": hashlib.sha256(raw).hexdigest(),
        "exact_passages": [
            "$1 + $0.20/min",
            "$143.90/year* ($99/year limited time offer available for new members)",
            "45 min free, then $0.20/min",
        ],
        "snapshot_file": "divvy_pricing.html",
    }


def main():
    RAW.mkdir(parents=True, exist_ok=True)
    grouped, archive_sha = fetch_source()
    scenarios = {
        "member": write_scenario("member", grouped, 0, [12, 12, 12, 12]),
        "sparse": write_scenario("sparse", grouped, 125, [1, 1, 1, 0]),
    }
    metadata = {
        "data_url": DATA_URL,
        "data_accessed_utc": datetime.now(timezone.utc).isoformat(),
        "zip_sha256": archive_sha,
        "selection_note": "Anonymized public trips are not a single rider. scenario_selected flags modeled frequency using genuine trip durations; 500 source rows per file.",
        "scenarios": scenarios,
        "pricing": save_pricing(),
    }
    (RAW / "divvy_sources.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps({"scenarios": scenarios, "pricing_sha256": metadata["pricing"]["html_sha256"]}, indent=2))


if __name__ == "__main__":
    main()
