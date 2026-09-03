"""
Initialize n10s in Neo4j and import W3C OWL 2 Ontology.
"""
import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USERNAME", "neo4j")
pwd = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(uri, auth=(user, pwd))

with driver.session() as session:
    print("1. Creating unique URI constraint for n10s...")
    try:
        session.run("CREATE CONSTRAINT n10s_unique_uri IF NOT EXISTS FOR (r:Resource) REQUIRE r.uri IS UNIQUE")
        print(" -> Constraint OK.")
    except Exception as e:
        print(f" -> Constraint note: {e}")

    print("2. Initializing n10s graph config...")
    try:
        res = session.run("CALL n10s.graphconfig.init({handleVocabUris: 'SHORTEN', handleMultival: 'ARRAY', keepLangTag: false})").data()
        print(" -> GraphConfig initialized OK:", res)
    except Exception as e:
        print(f" -> GraphConfig note: {e}")

    print("3. Importing mrp_ontology.ttl into Neo4j via n10s...")
    try:
        ontology_file = os.path.join(os.path.dirname(__file__), "..", "ontology", "mrp_ontology.ttl")
        with open(ontology_file, "r", encoding="utf-8") as f:
            ttl_payload = f.read()
        res = session.run("CALL n10s.onto.import.inline($payload, 'Turtle')", payload=ttl_payload).data()
        print(" -> Ontology imported successfully!")
        for r in res:
            print(f"    - Elements imported: {r}")
    except Exception as e:
        print(f" -> Import error: {e}")

    print("\n4. Checking imported Ontology Classes in Neo4j:")
    try:
        classes = session.run("MATCH (c:Class) RETURN c.uri AS uri, c.name AS name LIMIT 10").data()
        for c in classes:
            print(f"    - Class: {c.get('name', c.get('uri'))}")
    except Exception as e:
        print(f" -> Query error: {e}")

driver.close()
