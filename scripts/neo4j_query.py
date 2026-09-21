#!/usr/bin/env python3
"""
neo4j_query.py
==============
Main query runner for the Neo4j Knowledge Graph Skill.

Usage:
  python3 neo4j_query.py --action schema
  python3 neo4j_query.py --action query --cypher "MATCH (n) RETURN n LIMIT 10"
  python3 neo4j_query.py --action query --cypher "MATCH (n) RETURN n" --output json
  python3 neo4j_query.py --action query --cypher "MATCH (n) RETURN n" --output csv
  python3 neo4j_query.py --action count
"""

import argparse
import json
import os
import sys
import csv
import io
from datetime import datetime
from pathlib import Path

# ── Load .env ────────────────────────────────────────────────────────────────
def load_env():
    """Load environment variables from env/.env file."""
    # Search for env/.env relative to this script's location
    script_dir = Path(__file__).resolve().parent
    skill_dir = script_dir.parent
    env_path = skill_dir / "env" / ".env"

    if not env_path.exists():
        # Fallback: look in current working directory
        env_path = Path("env/.env")

    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, _, value = line.partition("=")
                    os.environ.setdefault(key.strip(), value.strip())
    else:
        print(f"⚠️  Warning: .env file not found at {env_path}. Using system environment variables.")

load_env()

# ── Try importing neo4j ───────────────────────────────────────────────────────
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

# ── Config ────────────────────────────────────────────────────────────────────
NEO4J_URI      = os.environ.get("NEO4J_URI", "")
NEO4J_USERNAME = os.environ.get("NEO4J_USERNAME", "")
NEO4J_PASSWORD = os.environ.get("NEO4J_PASSWORD", "")
NEO4J_DATABASE = os.environ.get("NEO4J_DATABASE", "neo4j")

if not all([NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD]):
    print("❌ Missing Neo4j credentials. Check env/.env file.")
    sys.exit(1)


# ── Driver ────────────────────────────────────────────────────────────────────
def get_driver():
    try:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USERNAME, NEO4J_PASSWORD))
        driver.verify_connectivity()
        return driver
    except neo4j_exceptions.ServiceUnavailable as e:
        print(f"❌ Cannot connect to Neo4j: {e}")
        print(f"   URI used: {NEO4J_URI}")
        print("   Check NEO4J_URI in env/.env")
        sys.exit(1)
    except neo4j_exceptions.AuthError as e:
        print(f"❌ Authentication failed: {e}")
        print("   Check NEO4J_USERNAME and NEO4J_PASSWORD in env/.env")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Connection error: {e}")
        sys.exit(1)


# ── Schema Action ─────────────────────────────────────────────────────────────
def get_schema(driver):
    """Extract full schema: labels, relationship types, and property keys."""
    results = {}

    with driver.session(database=NEO4J_DATABASE) as session:
        # Node labels
        node_labels = session.run("CALL db.labels() YIELD label RETURN label ORDER BY label").data()
        results["node_labels"] = [r["label"] for r in node_labels]

        # Relationship types
        rel_types = session.run("CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType ORDER BY relationshipType").data()
        results["relationship_types"] = [r["relationshipType"] for r in rel_types]

        # Property keys
        prop_keys = session.run("CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey ORDER BY propertyKey").data()
        results["property_keys"] = [r["propertyKey"] for r in prop_keys]

        # Node counts per label
        counts = {}
        for label in results["node_labels"]:
            try:
                count = session.run(f"MATCH (n:`{label}`) RETURN count(n) AS cnt").single()["cnt"]
                counts[label] = count
            except Exception:
                counts[label] = "?"
        results["node_counts"] = counts

        # Sample properties per label (first node's keys)
        label_props = {}
        for label in results["node_labels"]:
            try:
                sample = session.run(f"MATCH (n:`{label}`) RETURN keys(n) AS props LIMIT 1").single()
                label_props[label] = sample["props"] if sample else []
            except Exception:
                label_props[label] = []
        results["label_properties"] = label_props

    return results


def print_schema(schema):
    print("\n" + "="*60)
    print("📊  NEO4J KNOWLEDGE GRAPH — SCHEMA OVERVIEW")
    print("="*60)

    print(f"\n🏷️  NODE LABELS ({len(schema['node_labels'])} total):")
    for label in schema["node_labels"]:
        count = schema["node_counts"].get(label, "?")
        props = schema["label_properties"].get(label, [])
        props_str = ", ".join(props[:8]) + ("..." if len(props) > 8 else "")
        print(f"   • {label:<30} [{count} nodes]  props: {props_str}")

    print(f"\n🔗  RELATIONSHIP TYPES ({len(schema['relationship_types'])} total):")
    for rel in schema["relationship_types"]:
        print(f"   • {rel}")

    print(f"\n🔑  ALL PROPERTY KEYS ({len(schema['property_keys'])} total):")
    print("   " + ", ".join(schema["property_keys"]))

    print("\n" + "="*60)


# ── Query Action ──────────────────────────────────────────────────────────────
def flatten_record(record):
    """Flatten a neo4j record into a plain dict."""
    row = {}
    for key in record.keys():
        val = record[key]
        if hasattr(val, "_properties"):        # Node or Relationship
            props = dict(val._properties)
            if hasattr(val, "labels"):
                props["_labels"] = list(val.labels)
            if hasattr(val, "type"):
                props["_type"] = val.type
            row[key] = props
        elif isinstance(val, (dict,)):
            row[key] = val
        elif isinstance(val, list):
            row[key] = [str(v) for v in val]
        else:
            row[key] = val
    return row


def run_query(driver, cypher, output_format="table", limit_warn=500):
    """Run a Cypher query and return results."""
    print(f"\n🔍 Running query...")
    print(f"   Cypher: {cypher[:200]}{'...' if len(cypher) > 200 else ''}\n")

    with driver.session(database=NEO4J_DATABASE) as session:
        try:
            records = session.run(cypher).data()
        except neo4j_exceptions.CypherSyntaxError as e:
            print(f"❌ Cypher syntax error: {e}")
            sys.exit(1)
        except neo4j_exceptions.ClientError as e:
            print(f"❌ Query error: {e}")
            sys.exit(1)
        except Exception as e:
            print(f"❌ Error running query: {e}")
            sys.exit(1)

    if not records:
        print("ℹ️  Query returned 0 results.")
        return []

    # Flatten records
    flat_records = []
    for rec in records:
        flat = {}
        for k, v in rec.items():
            if hasattr(v, "_properties"):
                flat[k] = dict(v._properties)
            elif isinstance(v, list):
                flat[k] = v
            else:
                flat[k] = v
        flat_records.append(flat)

    total = len(flat_records)
    print(f"✅ {total} record(s) returned.\n")

    if output_format == "json":
        return output_json(flat_records)
    elif output_format == "csv":
        return output_csv(flat_records)
    else:
        return output_table(flat_records)


def output_table(records):
    if not records:
        return
    headers = list(records[0].keys())
    rows = []
    for rec in records:
        row = []
        for h in headers:
            val = rec.get(h, "")
            if isinstance(val, dict):
                val = json.dumps(val, ensure_ascii=False)[:80]
            elif isinstance(val, list):
                val = str(val)[:80]
            else:
                val = str(val)[:80] if val is not None else ""
            row.append(val)
        rows.append(row)

    if HAS_TABULATE:
        print(tabulate(rows, headers=headers, tablefmt="rounded_outline"))
    else:
        # Fallback plain table
        widths = [max(len(str(h)), max((len(str(r[i])) for r in rows), default=0)) for i, h in enumerate(headers)]
        sep = "+-" + "-+-".join("-" * w for w in widths) + "-+"
        print(sep)
        print("| " + " | ".join(str(h).ljust(widths[i]) for i, h in enumerate(headers)) + " |")
        print(sep)
        for row in rows:
            print("| " + " | ".join(str(v).ljust(widths[i]) for i, v in enumerate(row)) + " |")
        print(sep)
    return records


def output_json(records):
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"neo4j_results_{timestamp}.json"
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(records, f, indent=2, default=str, ensure_ascii=False)
    print(f"💾 Results saved to: {filename}")
    # Also print a snippet
    print(json.dumps(records[:3], indent=2, default=str, ensure_ascii=False))
    if len(records) > 3:
        print(f"   ... and {len(records) - 3} more records in {filename}")
    return records


def output_csv(records):
    if not records:
        return
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"neo4j_results_{timestamp}.csv"
    headers = list(records[0].keys())
    with open(filename, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=headers)
        writer.writeheader()
        for rec in records:
            cleaned = {k: json.dumps(v, default=str) if isinstance(v, (dict, list)) else v for k, v in rec.items()}
            writer.writerow(cleaned)
    print(f"💾 Results saved to: {filename}")
    return records


# ── Count Action ──────────────────────────────────────────────────────────────
def run_count(driver):
    """Show counts of all node labels."""
    print("\n📊 Node Counts by Label:\n")
    with driver.session(database=NEO4J_DATABASE) as session:
        records = session.run(
            "MATCH (n) RETURN labels(n) AS Labels, count(n) AS Count ORDER BY Count DESC"
        ).data()

    if HAS_TABULATE:
        rows = [(str(r["Labels"]), r["Count"]) for r in records]
        print(tabulate(rows, headers=["Label(s)", "Count"], tablefmt="rounded_outline"))
    else:
        for r in records:
            print(f"  {str(r['Labels']):<40} {r['Count']}")


# ── CLI ───────────────────────────────────────────────────────────────────────
def main():
    parser = argparse.ArgumentParser(
        description="Neo4j Knowledge Graph Query Tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python3 neo4j_query.py --action schema
  python3 neo4j_query.py --action count
  python3 neo4j_query.py --action query --cypher "MATCH (n:Payment) RETURN n LIMIT 10"
  python3 neo4j_query.py --action query --cypher "MATCH (n) RETURN n" --output json
  python3 neo4j_query.py --action query --cypher "MATCH (n) RETURN n" --output csv
        """
    )
    parser.add_argument("--action", choices=["schema", "query", "count"], required=True,
                        help="Action to perform")
    parser.add_argument("--cypher", type=str, default=None,
                        help="Cypher query string (required for --action query)")
    parser.add_argument("--output", choices=["table", "json", "csv"], default="table",
                        help="Output format (default: table)")

    args = parser.parse_args()

    print(f"\n🔌 Connecting to Neo4j: {NEO4J_URI}")
    driver = get_driver()
    print(f"✅ Connected to database: {NEO4J_DATABASE}\n")

    if args.action == "schema":
        schema = get_schema(driver)
        print_schema(schema)

    elif args.action == "query":
        if not args.cypher:
            print("❌ --cypher is required for --action query")
            sys.exit(1)
        run_query(driver, args.cypher, output_format=args.output)

    elif args.action == "count":
        run_count(driver)

    driver.close()


if __name__ == "__main__":
    main()
