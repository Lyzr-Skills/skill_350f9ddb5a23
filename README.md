# 🕸️ Neo4j Knowledge Graph Skill

Extract, query, explore, and export data from your Neo4j Knowledge Graph using
natural language or Cypher queries.

---

## 📁 Folder Structure

```
neo4j_knowledge_graph/
├── SKILL.md                        ← Agent instructions (read this first)
├── README.md                       ← This file
├── env/
│   └── .env                        ← 🔐 Your Neo4j credentials (KEEP PRIVATE)
├── scripts/
│   ├── neo4j_query.py              ← Main query runner
│   ├── neo4j_explorer.py           ← Schema & relationship explorer
│   ├── neo4j_export.py             ← Bulk data exporter
│   └── install_deps.sh             ← Install Python dependencies
└── references/
    └── cypher_cheatsheet.md        ← Common Cypher patterns
```

---

## ⚡ Quick Start

### 1. Install dependencies
```bash
bash scripts/install_deps.sh
# or manually:
pip install neo4j python-dotenv tabulate pandas
```

### 2. Verify credentials in env/.env
```env
NEO4J_URI=neo4j+s://463ec022.databases.neo4j.io
NEO4J_USERNAME=463ec022
NEO4J_PASSWORD=<your_password>
NEO4J_DATABASE=463ec022
```

### 3. Test connection & explore schema
```bash
python3 scripts/neo4j_query.py --action schema
```

---

## 🛠️ Script Usage

### neo4j_query.py — Main Query Runner

```bash
# Explore schema
python3 scripts/neo4j_query.py --action schema

# Count nodes by label
python3 scripts/neo4j_query.py --action count

# Run a query (table output)
python3 scripts/neo4j_query.py --action query \
  --cypher "MATCH (n:Payment) RETURN n LIMIT 25"

# Export to JSON
python3 scripts/neo4j_query.py --action query \
  --cypher "MATCH (n:Payment) RETURN n" --output json

# Export to CSV
python3 scripts/neo4j_query.py --action query \
  --cypher "MATCH (n:Payment) RETURN n" --output csv
```

### neo4j_explorer.py — Schema Explorer

```bash
# Explore a specific label
python3 scripts/neo4j_explorer.py --label Payment

# Show label + its relationships
python3 scripts/neo4j_explorer.py --label Payment --relationships

# Sample records
python3 scripts/neo4j_explorer.py --sample Payment --limit 3

# Explore a relationship type
python3 scripts/neo4j_explorer.py --relationship PAID_BY

# Find paths between node types
python3 scripts/neo4j_explorer.py --paths --from Customer --to Invoice
```

### neo4j_export.py — Bulk Exporter

```bash
# Export all nodes to JSON
python3 scripts/neo4j_export.py --format json

# Export specific label to CSV
python3 scripts/neo4j_export.py --format csv --label Payment

# Export everything (nodes + relationships) to both formats
python3 scripts/neo4j_export.py --format both --include-relationships

# Custom limit and output directory
python3 scripts/neo4j_export.py --format json --limit 5000 --output-dir my_export/
```

---

## 💡 Example Queries

| Ask the agent... | What it does |
|------------------|--------------|
| "Show me payment details" | Queries Payment nodes with all properties |
| "Get all customers" | Fetches Customer nodes |
| "Find payment ID PAY-001" | Filters by specific ID |
| "What's in the graph?" | Runs schema + count overview |
| "Export payments to CSV" | Runs export script with CSV format |
| "Find connections between Customer and Invoice" | Runs path-finding query |
| "How many payments are completed?" | Runs aggregation with status filter |

---

## 🔐 Security Notes

- Keep `env/.env` private — do not commit to git.
- Add `env/.env` to your `.gitignore`.
- The credentials connect to Neo4j Aura (cloud-hosted, encrypted with `neo4j+s://`).
