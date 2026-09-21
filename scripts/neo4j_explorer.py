#!/usr/bin/env python3
"""
neo4j_explorer.py
=================
Interactive schema explorer for the Neo4j Knowledge Graph.
Provides detailed exploration of specific node labels and relationships.

Usage:
  python3 neo4j_explorer.py --label Payment
  python3 neo4j_explorer.py --label Customer --relationships
  python3 neo4j_explorer.py --relationship PAID_BY
  python3 neo4j_explorer.py --sample Payment --limit 5
  python3 neo4j_explorer.py --paths --from Customer --to Invoice
"""

import argparse
import json
import os
import sys
from pathlib import Path


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

try:
    from tabulate import tabulate
    HAS_TABULATE = True
except ImportError:
    HAS_TABULATE = False

NEO4J_URI      = os.environ.get("NEO4J_URI", "")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")


def get_driver():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        driver.verify_connectivity()
        return driver
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        sys.exit(1)


def explore_label(driver, label, show_relationships=False):
    """Deep dive into a specific node label."""
    print(f"\n{'='*60}")
    print(f"🔍  Exploring Node Label: {label}")
    print(f"{'='*60}")

    with driver.session(database=NEO4J_DATABASE) as session:
        # Count
        count = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS cnt").single()["cnt"]
        print(f"\n📊 Total nodes: {count}")

        # Sample properties
        sample = session.run(f"MATCH (n:`{label}`) RETURN n LIMIT 1").single()
        if sample:
            node = sample["n"]
            props = dict(node._properties)
            print(f"\n🔑 Properties ({len(props)} keys):")
            for k, v in props.items():
                print(f"   {k}: {type(v).__name__} = {str(v)[:60]}")

        # Relationships
        if show_relationships:
            print(f"\n🔗 Outgoing Relationships from {label}:")
            out_rels = session.run(
                f"MATCH (n:`{label}`)-[r]->(m) RETURN DISTINCT type(r) AS RelType, labels(m) AS TargetLabel, count(*) AS Count ORDER BY Count DESC LIMIT 20"
            ).data()
            if out_rels:
                for r in out_rels:
                    print(f"   ({label})-[:{r['RelType']}]->({r['TargetLabel']})  ×{r['Count']}")
            else:
                print("   None found.")

            print(f"\n🔗 Incoming Relationships to {label}:")
            in_rels = session.run(
                f"MATCH (m)-[r]->(n:`{label}`) RETURN DISTINCT type(r) AS RelType, labels(m) AS SourceLabel, count(*) AS Count ORDER BY Count DESC LIMIT 20"
            ).data()
            if in_rels:
                for r in in_rels:
                    print(f"   ({r['SourceLabel']})-[:{r['RelType']}]->({label})  ×{r['Count']}")
            else:
                print("   None found.")


def sample_nodes(driver, label, limit=5):
    """Show sample nodes for a label."""
    print(f"\n📋  Sample {limit} nodes of type: {label}\n")
    with driver.session(database=NEO4J_DATABASE) as session:
        records = session.run(f"MATCH (n:`{label}`) RETURN n LIMIT {limit}").data()
        for i, rec in enumerate(records, 1):
            node = rec["n"]
            props = dict(node._properties)
            print(f"  [{i}] {json.dumps(props, default=str, indent=6)}")


def explore_relationship(driver, rel_type):
    """Explore a specific relationship type."""
    print(f"\n{'='*60}")
    print(f"🔗  Exploring Relationship: {rel_type}")
    print(f"{'='*60}")

    with driver.session(database=NEO4J_DATABASE) as session:
        count = session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) AS cnt").single()["cnt"]
        print(f"\n📊 Total relationships: {count}")

        endpoints = session.run(
            f"MATCH (a)-[r:`{rel_type}`]->(b) RETURN DISTINCT labels(a) AS From, labels(b) AS To, count(*) AS Count ORDER BY Count DESC LIMIT 10"
        ).data()
        print("\n📍 Endpoints:")
        for ep in endpoints:
            print(f"   {ep['From']} -[:{rel_type}]-> {ep['To']}  ×{ep['Count']}")

        # Sample rel properties
        sample = session.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN r LIMIT 1").single()
        if sample:
            rel = sample["r"]
            props = dict(rel._properties)
            if props:
                print(f"\n🔑 Relationship properties: {json.dumps(props, default=str)}")


def find_paths(driver, from_label, to_label, max_hops=3):
    """Find paths between two node types."""
    print(f"\n🛤️  Finding paths: ({from_label}) → ({to_label}) [max {max_hops} hops]\n")
    with driver.session(database=NEO4J_DATABASE) as session:
        cypher = (
            f"MATCH path = (a:`{from_label}`)-[*1..{max_hops}]-(b:`{to_label}`) "
            f"RETURN [n IN nodes(path) | labels(n)] AS NodePath, "
            f"[r IN relationships(path) | type(r)] AS RelPath "
            f"LIMIT 10"
        )
        records = session.run(cypher).data()
        if not records:
            print("  No paths found.")
            return
        seen = set()
        for rec in records:
            key = str(rec["RelPath"])
            if key not in seen:
                seen.add(key)
                node_labels = [str(n) for n in rec["NodePath"]]
                rels = rec["RelPath"]
                path_str = ""
                for i, n in enumerate(node_labels):
                    path_str += n
                    if i < len(rels):
                        path_str += f" -[:{rels[i]}]-> "
                print(f"  {path_str}")


def main():
    parser = argparse.ArgumentParser(description="Neo4j Knowledge Graph Explorer")
    parser.add_argument("--label", type=str, help="Node label to explore")
    parser.add_argument("--relationships", action="store_true", help="Show relationships for label")
    parser.add_argument("--relationship", type=str, help="Specific relationship type to explore")
    parser.add_argument("--sample", type=str, help="Show sample nodes for this label")
    parser.add_argument("--limit", type=int, default=5, help="Number of sample nodes (default: 5)")
    parser.add_argument("--paths", action="store_true", help="Find paths between two labels")
    parser.add_argument("--from", dest="from_label", type=str, help="Source label for path finding")
    parser.add_argument("--to", dest="to_label", type=str, help="Target label for path finding")
    parser.add_argument("--max-hops", type=int, default=3, help="Max hops for path finding")

    args = parser.parse_args()

    print(f"\n🔌 Connecting to Neo4j: {NEO4J_URI}")
    driver = get_driver()
    print(f"✅ Connected to database: {NEO4J_DATABASE}")

    if args.label:
        explore_label(driver, args.label, show_relationships=args.relationships)
    if args.sample:
        sample_nodes(driver, args.sample, limit=args.limit)
    if args.relationship:
        explore_relationship(driver, args.relationship)
    if args.paths and args.from_label and args.to_label:
        find_paths(driver, args.from_label, args.to_label, max_hops=args.max_hops)

    if not any([args.label, args.sample, args.relationship, args.paths]):
        parser.print_help()

    driver.close()


if __name__ == "__main__":
    main()
