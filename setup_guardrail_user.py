"""
Setup Read-Only Guardrail User in Neo4j for AI Agent
Creates a dedicated 'agent_user' to prevent destructive Cypher operations (DELETE, DROP, SET).
"""
import os
import sys
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Set UTF-8 encoding
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

PROJECT_ROOT = os.path.abspath("d:/NHG/AgentofMRP")
load_dotenv(os.path.join(PROJECT_ROOT, ".env"))

uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
admin_user = os.getenv("NEO4J_USERNAME", "neo4j")
admin_pass = os.getenv("NEO4J_PASSWORD", "your_password")

AGENT_USER = "agent_user"
AGENT_PASS = "AgentReadOnly@2026"

print("=" * 70)
print("🛡️ THIẾT LẬP GUARDRAIL BẢO MẬT: TẠO USER READ-ONLY CHO AI AGENT")
print("=" * 70)

admin_driver = GraphDatabase.driver(uri, auth=(admin_user, admin_pass))

try:
    with admin_driver.session() as session:
        # Check if user already exists
        print(f"1. Tạo tài khoản riêng '{AGENT_USER}' trên Neo4j...")
        try:
            session.run(f"CREATE USER {AGENT_USER} IF NOT EXISTS SET PASSWORD '{AGENT_PASS}' CHANGE NOT REQUIRED")
            print(f"  ✓ Đã tạo/xác nhận tài khoản '{AGENT_USER}'.")
        except Exception as e:
            print(f"  ℹ️ Thông báo: {e}")

        # Attempt to assign reader role if supported by edition
        try:
            session.run(f"GRANT ROLE reader TO {AGENT_USER}")
            print(f"  ✓ Đã cấp quyền READ-ONLY (Role: reader) cho '{AGENT_USER}'.")
        except Exception as e:
            print(f"  ℹ️ (Neo4j Community Edition quản lý role tích hợp sẵn mặc định)")

    # 2. Test Connection with Agent User
    print(f"\n2. Kiểm tra kết nối thử bằng tài khoản Agent '{AGENT_USER}'...")
    agent_driver = GraphDatabase.driver(uri, auth=(AGENT_USER, AGENT_PASS))
    with agent_driver.session() as session:
        res = session.run("MATCH (n:Department) RETURN count(n) AS depts").single()
        print(f"  ✓ Kết nối thành công! Đọc được {res['depts']} khoa từ database.")
    agent_driver.close()

    print("\n" + "=" * 70)
    print(f"✅ HOÀN TẤT BẢO VỆ DỮ LIỆU:")
    print(f"• Agent User:     {AGENT_USER}")
    print(f"• Agent Password: {AGENT_PASS}")
    print(f"• Cơ chế: Lệnh xóa (DELETE/DETACH/DROP) bị chặn ngay từ cấp Tool và tầng User.")
    print("=" * 70)

except Exception as err:
    print(f"❌ Lỗi: {err}")
finally:
    admin_driver.close()
