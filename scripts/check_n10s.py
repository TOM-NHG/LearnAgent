import os
from dotenv import load_dotenv
from neo4j import GraphDatabase

load_dotenv()
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USERNAME", "neo4j")
pwd = os.getenv("NEO4J_PASSWORD", "your_password")

driver = GraphDatabase.driver(uri, auth=(user, pwd))
with driver.session() as session:
    try:
        procs = session.run("SHOW PROCEDURES YIELD name WHERE name STARTS WITH 'n10s' RETURN name").data()
        print(f"n10s procedures available: {len(procs)}")
        for p in procs[:5]:
            print(f" - {p['name']}")
    except Exception as e:
        print(f"Error checking n10s: {e}")
driver.close()
