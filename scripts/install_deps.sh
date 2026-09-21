#!/bin/bash
# ============================================================
# install_deps.sh
# Installs all Python dependencies for the Neo4j skill
# ============================================================

echo "📦 Installing Neo4j Knowledge Graph Skill Dependencies..."
echo ""

pip install neo4j python-dotenv tabulate pandas

echo ""
echo "✅ Dependencies installed successfully!"
echo ""
echo "🔌 Test your connection with:"
echo "   python3 scripts/neo4j_query.py --action schema"
