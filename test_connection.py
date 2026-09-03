"""
Test Connection to Neo4j Graph Database using langchain_neo4j
"""
import os
import sys
from dotenv import load_dotenv
from langchain_neo4j import Neo4jGraph

# Set UTF-8 encoding for console output in Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. Load environment variables
load_dotenv()

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
username = os.getenv("NEO4J_USERNAME", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "your_password")

print(f"Connecting to Neo4j at {uri} with user '{username}'...")

try:
    # 2. Connect to Neo4j via official langchain_neo4j package
    graph = Neo4jGraph(
        url=uri,
        username=username,
        password=password,
        enhanced_schema=False
    )
    
    # 3. Refresh and print schema
    graph.refresh_schema()
    print("=" * 60)
    print("SUCCESS: KET NOI NEO4J THANH CONG!")
    print("=" * 60)
    print("Graph Schema hien tai:")
    print(graph.schema if graph.schema.strip() else "(Graph database hien dang trong, san sang nap du lieu ontology)")
    print("=" * 60)

except Exception as e:
    print("=" * 60)
    print("ERROR: LOI KET NOI NEO4J:")
    print(str(e))
    print("=" * 60)
