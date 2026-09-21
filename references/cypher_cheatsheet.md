# Cypher Query Cheatsheet
## Neo4j Knowledge Graph — Common Patterns

---

## 1. Schema & Discovery

```cypher
-- All node labels
CALL db.labels() YIELD label RETURN label

-- All relationship types
CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType

-- All property keys
CALL db.propertyKeys() YIELD propertyKey RETURN propertyKey

-- Count all nodes by label
MATCH (n) RETURN labels(n) AS Label, count(n) AS Count ORDER BY Count DESC

-- Sample one node per label (schema discovery)
MATCH (n:Payment) RETURN keys(n) LIMIT 1
```

---

## 2. Basic Node Queries

```cypher
-- Get all nodes of a type
MATCH (n:Payment) RETURN n LIMIT 50

-- Get specific properties
MATCH (n:Payment) RETURN n.id, n.amount, n.status, n.date LIMIT 50

-- Filter by property value
MATCH (n:Payment) WHERE n.status = 'completed' RETURN n LIMIT 50

-- Filter by multiple conditions
MATCH (n:Payment) WHERE n.amount > 1000 AND n.status = 'completed' RETURN n

-- Text search (case-insensitive)
MATCH (n:Customer) WHERE toLower(n.name) CONTAINS 'john' RETURN n

-- Search by ID
MATCH (n) WHERE n.id = 'PAY-001' RETURN n
```

---

## 3. Relationship Queries

```cypher
-- All relationships of a type
MATCH (a)-[r:PAID_BY]->(b) RETURN a, r, b LIMIT 50

-- Node with its relationships
MATCH (p:Payment)-[r]-(related) RETURN p, type(r) AS RelType, related LIMIT 50

-- Outgoing only
MATCH (p:Payment)-[r]->(b) RETURN p, type(r), b LIMIT 50

-- Incoming only
MATCH (a)-[r]->(p:Payment) RETURN a, type(r), p LIMIT 50

-- Specific relationship path
MATCH (c:Customer)-[:MADE]->(p:Payment)-[:FOR]->(i:Invoice)
RETURN c.name, p.amount, i.invoice_number LIMIT 50
```

---

## 4. Aggregations

```cypher
-- Count nodes
MATCH (n:Payment) RETURN count(n) AS TotalPayments

-- Sum values
MATCH (n:Payment) RETURN sum(n.amount) AS TotalAmount

-- Average
MATCH (n:Payment) RETURN avg(n.amount) AS AvgAmount

-- Group by
MATCH (n:Payment) RETURN n.status AS Status, count(n) AS Count ORDER BY Count DESC

-- Min / Max
MATCH (n:Payment) RETURN min(n.amount) AS MinAmount, max(n.amount) AS MaxAmount

-- Collect into list
MATCH (c:Customer)-[:MADE]->(p:Payment)
RETURN c.name AS Customer, collect(p.amount) AS Payments
```

---

## 5. Path Finding

```cypher
-- Shortest path between two nodes
MATCH (a:Customer {id: 'CUST-001'}), (b:Invoice {id: 'INV-001'})
MATCH path = shortestPath((a)-[*]-(b))
RETURN path

-- All paths up to 3 hops
MATCH path = (a:Customer)-[*1..3]-(b:Payment) RETURN path LIMIT 10

-- Paths between label types
MATCH path = (a:Customer)-[*1..2]-(b:Invoice) 
RETURN [n IN nodes(path) | labels(n)] AS NodePath,
       [r IN relationships(path) | type(r)] AS RelPath
LIMIT 20
```

---

## 6. Payment-Specific Patterns

```cypher
-- All payment details with customer
MATCH (p:Payment)
OPTIONAL MATCH (p)-[:PAID_BY]->(c:Customer)
OPTIONAL MATCH (p)-[:FOR_INVOICE]->(i:Invoice)
RETURN p.id AS PaymentID,
       p.amount AS Amount,
       p.currency AS Currency,
       p.status AS Status,
       p.date AS Date,
       c.name AS CustomerName,
       i.invoice_number AS InvoiceNo
ORDER BY p.date DESC
LIMIT 50

-- Failed/pending payments
MATCH (p:Payment) WHERE p.status IN ['failed', 'pending'] 
RETURN p ORDER BY p.date DESC LIMIT 50

-- Payments above threshold
MATCH (p:Payment) WHERE p.amount > 5000 
RETURN p ORDER BY p.amount DESC LIMIT 50

-- Recent payments (last 30 days - adjust based on your date format)
MATCH (p:Payment) 
WHERE p.date >= '2024-01-01'
RETURN p ORDER BY p.date DESC LIMIT 50
```

---

## 7. Update & Write (use with caution)

```cypher
-- Set a property
MATCH (n:Payment {id: 'PAY-001'}) SET n.status = 'reviewed' RETURN n

-- Add a label
MATCH (n {id: 'PAY-001'}) SET n:Reviewed RETURN n

-- Create a relationship
MATCH (c:Customer {id: 'CUST-001'}), (p:Payment {id: 'PAY-001'})
MERGE (c)-[:MADE]->(p)
```

---

## 8. Useful Utilities

```cypher
-- Random sample
MATCH (n:Payment) RETURN n ORDER BY rand() LIMIT 10

-- Nodes with most connections
MATCH (n)-[r]-()
RETURN labels(n) AS Label, n.id AS ID, count(r) AS Connections
ORDER BY Connections DESC LIMIT 20

-- Orphan nodes (no relationships)
MATCH (n) WHERE NOT (n)--() RETURN n LIMIT 20

-- Duplicate property check
MATCH (n:Payment)
WITH n.id AS id, collect(n) AS nodes
WHERE size(nodes) > 1
RETURN id, size(nodes) AS Duplicates
```
