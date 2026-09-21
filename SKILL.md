---
name: neo4j-knowledge-graph
description: >
  Connects to a Neo4j Knowledge Graph database and extracts, queries, and analyzes
  graph data including nodes, relationships, paths, and properties. Use this skill
  WHENEVER the user asks about data stored in the knowledge graph, mentions querying
  Neo4j, asks to "get", "fetch", "find", "retrieve", "show", "list", or "extract"
  any kind of entity or information (e.g., payment details, customer records, 
  transaction history, invoices, products, orders, users, nodes, relationships).
  Also trigger this skill when the user asks to explore graph structure, run Cypher
  queries, summarize graph contents, detect patterns, find connections between 
  entities, or analyze any data that lives in Neo4j. If the user mentions any 
  business term like "payment", "invoice", "order", "customer", "product", "account",
  or any other domain entity — always check the knowledge graph first using this skill.
compatibility:
  tools: [bash, python3]
  dependencies: [neo4j, python-dotenv, tabulate, pandas]
---

# Neo4j Knowledge Graph Skill

You have full access to a Neo4j knowledge graph. Your job is to understand what the
user is asking for in plain English and translate it into effective Cypher queries,
run them using the provided scripts, and return clear, well-formatted results.

## Environment Setup

All credentials are stored in `env/.env` (relative to this skill directory).
The scripts load these automatically — you do not need to ask the user for credentials.

```
env/.env  ←  NEO4J_URI, NEO4J_USERNAME, NEO4J_PASSWORD, NEO4J_DATABASE
```

If the `.env` file is missing or credentials fail, tell the user to check `env/.env`.

---

## Your Core Capabilities

### 1. EXPLORE the Graph Schema
When the user wants to understand what's in the graph (nodes, labels, relationships):
```bash
python3 scripts/neo4j_query.py --action schema
```
This returns all node labels, relationship types, and property keys.

### 2. QUERY Nodes and Data
When the user asks for specific records (e.g., "show me payment details", "get all customers"):
```bash
python3 scripts/neo4j_query.py --action query --cypher "MATCH (n:Payment) RETURN n LIMIT 25"
```

### 3. SEARCH by Property
When the user wants to find something by a value (e.g., "find payment ID 1234"):
```bash
python3 scripts/neo4j_query.py --action query --cypher "MATCH (n) WHERE n.id = '1234' RETURN n"
```

### 4. EXTRACT Relationships / Paths
When the user wants connections between entities:
```bash
python3 scripts/neo4j_query.py --action query --cypher "MATCH (a)-[r]->(b) RETURN a, type(r), b LIMIT 50"
```

### 5. SUMMARIZE / COUNT
When the user wants aggregates or counts:
```bash
python3 scripts/neo4j_query.py --action query --cypher "MATCH (n) RETURN labels(n) AS Type, count(n) AS Count ORDER BY Count DESC"
```

### 6. EXPORT Data
To export results to JSON or CSV:
```bash
python3 scripts/neo4j_query.py --action query --cypher "MATCH (n:Payment) RETURN n" --output json
python3 scripts/neo4j_query.py --action query --cypher "MATCH (n:Payment) RETURN n" --output csv
```

### 7. RUN Custom Cypher
The user may provide their own Cypher query:
```bash
python3 scripts/neo4j_query.py --action query --cypher "<user_cypher_query>"
```

---

## How to Handle Common User Requests

### "Show me payment details" / "Get payment info" / "Payment data"
1. First run schema to find the correct Payment node label and properties.
2. Then query: `MATCH (p:Payment) RETURN p LIMIT 50`
3. If payment has relationships (e.g., to Customer, Invoice), include them:
   `MATCH (p:Payment)-[r]-(related) RETURN p, type(r), related LIMIT 50`

### "Find customer [name/id]"
1. `MATCH (c:Customer) WHERE c.name CONTAINS 'John' OR c.id = 'CUST001' RETURN c`

### "Show transactions / invoices / orders"
1. Get schema first, find correct label.
2. Query the matching label with LIMIT 50.

### "What's in the graph?" / "What data do you have?"
1. Run `--action schema` to describe the full structure.
2. Run a count query to show volumes.
3. Summarize for the user in plain English.

### "Find connections between X and Y"
1. `MATCH path = (a:LabelA)-[*1..3]-(b:LabelB) RETURN path LIMIT 20`

### "Export / download the data"
1. Run with `--output csv` or `--output json`.
2. The file is saved in the working directory and you can share it.

---

## Cypher Writing Guidelines

- ALWAYS use `LIMIT` on MATCH queries (default 50, increase only if user requests more).
- Use `OPTIONAL MATCH` when relationships might not exist.
- For text search, use `CONTAINS`, `STARTS WITH`, or `toLower()` for case-insensitivity.
- Prefer returning node properties directly: `RETURN n.id, n.name, n.amount` over `RETURN n`
  when presenting to the user (cleaner output).
- Use `ORDER BY` for cleaner results.
- For aggregations: `count()`, `sum()`, `avg()`, `collect()`.

### Example: Payment with related entities
```cypher
MATCH (p:Payment)
OPTIONAL MATCH (p)-[:PAID_BY]->(c:Customer)
OPTIONAL MATCH (p)-[:FOR_INVOICE]->(i:Invoice)
RETURN p.id AS PaymentID,
       p.amount AS Amount,
       p.status AS Status,
       p.date AS Date,
       c.name AS CustomerName,
       i.invoice_number AS InvoiceNo
ORDER BY p.date DESC
LIMIT 50
```

---

## Output Formatting Rules

- For small result sets (< 20 rows): show as a formatted table in the response.
- For large result sets (> 20 rows): summarize and offer to export.
- Always tell the user HOW MANY records were returned.
- If the query returns no results, say so clearly and suggest alternatives.
- For graph/path queries, describe the relationships in plain English.
- ALWAYS include the Cypher you used so the user can learn/reuse it.

---

## Error Handling

| Error | Action |
|-------|--------|
| `ServiceUnavailable` | Check `env/.env` URI — tell user to verify `NEO4J_URI`. |
| `AuthError` | Credentials wrong — tell user to update `env/.env`. |
| `ClientError` / Syntax | Fix the Cypher and retry. |
| `No results` | Try schema first, adjust query, inform user. |
| Label not found | Run schema, suggest correct label names. |

---

## Step-by-Step Workflow for ANY Graph Request

1. **Understand** the user's intent in plain English.
2. **If uncertain about schema**, run `--action schema` first.
3. **Build** the appropriate Cypher query.
4. **Execute** via `scripts/neo4j_query.py`.
5. **Format** the results clearly (table, summary, or export).
6. **Explain** what was found and offer follow-up options.

Always be proactive: if the user asks about "payments", also offer to show related
customers or invoices if those relationships exist. Surface the full picture.

---

## Script Reference

| Script | Purpose |
|--------|---------|
| `scripts/neo4j_query.py` | Main query runner — schema, query, export |
| `scripts/neo4j_explorer.py` | Interactive schema explorer and graph visualizer |
| `scripts/neo4j_export.py` | Bulk export of all nodes/relationships |

See `references/cypher_cheatsheet.md` for common query patterns.
