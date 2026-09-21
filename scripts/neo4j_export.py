#!/usr/bin/env python3
"""
neo4j_export.py
===============
Bulk export of all nodes and relationships from the Neo4j Knowledge Graph.
Exports to JSON, CSV, or both.

Usage:
  python3 neo4j_export.py --format json
  python3 neo4j_export.py --format csv
  python3 neo4j_export.py --format both
  python3 neo4j_export.py --format json --label Payment
  python3 neo4j_export.py --format csv --label Customer --limit 1000
"""

import argparse
import json
import csv
import os
import sys
from pathlib import Path
from datetime import datetime


# ── Load .env ──────────────────────────────────────────────────────────────────
def load_env():
    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    env_path = skill_dir / "env" / ".env"
    if not env_path.exists():
        env_path = Path("env/.env")
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())

load_env()

try:
    from neo4j import GraphDatabase, exceptions as neo4j_exceptions
except ImportError:
    print("❌ neo4j driver not installed. Run: pip install neo4j")
    sys.exit(1)

NEO4J_URI      = os.environ.get("NEO4J_URI", "")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

TIMESTAMP = datetime.now().strftime("%Y%m%d_%H%M%S")


def get_driver():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        driver.verify_connectivity()
        return driver
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)


def get_all_labels(driver):
    with driver.session(database=NEO4J_DATABASE) as session:
        records = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label").data()
        return [r["label"] for r in records]


def export_label_json(driver, label, limit, output_dir):
    """Export all nodes of a label to a JSON file."""
    with driver.session(database=NEO4J_DATABASE) as session:
        records = session.run(
            f"MATCH (n:`{label}`) RETURN n LIMIT {limit}"
        ).data()

    nodes = []
    for rec in records:
        node = rec["n"]
        node_dict = dict(node._properties)
        node_dict["_id"] = node.element_id
        node_dict["_labels"] = list(node.labels)
        nodes.append(node_dict)

    filename = output_dir / f"{label}_{TIMESTAMP}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(nodes, f, indent=2, default=str, ensure_ascii=False)
    print(f"  ✅ {label}: {len(nodes)} nodes → {filename}")
    return len(nodes)


def export_label_csv(driver, label, limit, output_dir):
    """Export all nodes of a label to a CSV file."""
    with driver.session(database=NEO4J_DATABASE) as session:
        records = session.run(
            f"MATCH (n:`{label}`) RETURN n LIMIT {limit}"
        ).data()

    if not records:
        print(f"  ⚠️  {label}: 0 nodes found, skipping.")
        return 0

    nodes = []
    all_keys = set()
    for rec in records:
        node = rec["n"]
        node_dict = dict(node._properties)
        node_dict["_id"] = node.element_id
        node_dict["_labels"] = ",".join(node.labels)
        nodes.append(node_dict)
        all_keys.update(node_dict.keys())

    headers = sorted(all_keys)
    filename = output_dir / f"{label}_{TIMESTAMP}.csv"
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers, extrasaction="ignore")
        writer.writeheader()
        for node in nodes:
            cleaned = {k: (json.dumps(v, default=str) if isinstance(v, (dict, list)) else v)
                       for k, v in node.items()}
            writer.writerow({h: cleaned.get(h, "") for h in headers})
    print(f"  ✅ {label}: {len(nodes)} nodes → {filename}")
    return len(nodes)


def export_relationships_json(driver, limit, output_dir):
    """Export all relationships to a JSON file."""
    with driver.session(database=NEO4J_DATABASE) as session:
        records = session.run(
            f"MATCH (a)-[r]->(b) RETURN "
            f"a.id AS source_id, labels(a) AS source_labels, "
            f"type(r) AS relationship, properties(r) AS rel_props, "
            f"b.id AS target_id, labels(b) AS target_labels "
            f"LIMIT {limit}"
        ).data()

    filename = output_dir / f"relationships_{TIMESTAMP}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str, ensure_ascii=False)
    print(f"  ✅ Relationships: {len(records)} → {filename}")
    return len(records)


def main():
    parser = argparse.ArgumentParser(description="Neo4j Bulk Export Tool")
    parser.add_argument("--format", choices=["json", "csv", "both"], default="json",
                        help="Export format")
    parser.add_argument("--label", type=str, default=None,
                        help="Specific node label to export (default: all labels)")
    parser.add_argument("--limit", type=int, default=10000,
                        help="Max nodes per label (default: 10000)")
    parser.add_argument("--include-relationships", action="store_true",
                        help="Also export relationships")
    parser.add_argument("--output-dir", type=str, default="neo4j_export",
                        help="Output directory (default: neo4j_export/)")
    args = parser.parse_args()

    # Create output directory
    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n🔌 Connecting to Neo4j: {NEO4J_URI}")
    driver = get_driver()
    print(f"✅ Connected to database: {NEO4J_DATABASE}")
    print(f"📁 Output directory: {output_dir.resolve()}\n")

    labels = [args.label] if args.label else get_all_labels(driver)
    print(f"📦 Exporting {len(labels)} label(s): {labels}\n")

    total_nodes = 0
    for label in labels:
        if args.format in ("json", "both"):
            total_nodes += export_label_json(driver, label, args.limit, output_dir)
        if args.format in ("csv", "both"):
            export_label_csv(driver, label, args.limit, output_dir)

    if args.include_relationships:
        print("\n🔗 Exporting relationships...")
        export_relationships_json(driver, args.limit * len(labels), output_dir)

    print(f"\n🎉 Export complete! {total_nodes} total nodes exported to {output_dir.resolve()}/")
    driver.close()


if __name__ == "__main__":
    main()
