"""
Ingest Cleaned MRP Datasets into Neo4j Graph Database
Creates Constraints, Indexes, Nodes, and Relationships using batch Cypher transactions.
"""
import os
import sys
import time
import pandas as pd
from dotenv import load_dotenv
from neo4j import GraphDatabase

# Set UTF-8 encoding for console output in Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# 1. Setup paths and load environment variables
PROJECT_ROOT = os.path.abspath("d:/NHG/AgentofMRP")
CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "cleaned")
RAW_DIR = os.path.join(PROJECT_ROOT, "data")
ML_DIR = os.path.join(PROJECT_ROOT, "data", "ml_ready")

load_dotenv(os.path.join(PROJECT_ROOT, ".env"))
uri = os.getenv("NEO4J_URI", "bolt://localhost:7687")
user = os.getenv("NEO4J_USERNAME", "neo4j")
password = os.getenv("NEO4J_PASSWORD", "your_password")

print("=" * 70)
print("🚀 BẮT ĐẦU NẠP DỮ LIỆU ONTOLOGY VÀO NEO4J GRAPH DATABASE...")
print(f"🔗 Kết nối: {uri} (User: {user})")
print("=" * 70)

driver = GraphDatabase.driver(uri, auth=(user, password))

def run_cypher(query, params=None):
    with driver.session() as session:
        return session.run(query, params or {}).consume()

def batch_insert(query, records, batch_size=500, desc=""):
    total = len(records)
    start_time = time.time()
    for i in range(0, total, batch_size):
        chunk = records[i:i + batch_size]
        with driver.session() as session:
            session.run(query, {"batch": chunk})
    elapsed = time.time() - start_time
    print(f"  ✓ {desc}: Nạp thành công {total:,} bản ghi ({elapsed:.2f}s)")

# -------------------------------------------------------------
# 2. CREATE CONSTRAINTS & INDEXES
# -------------------------------------------------------------
print("\n[Bước 1/7] Tạo ràng buộc duy nhất (Constraints) & Chỉ mục (Indexes)...")
constraints = [
    ("Department", "id", "dept_id_unique"),
    ("Major", "name", "major_name_unique"),
    ("Student", "id", "student_id_unique"),
    ("Invoice", "id", "invoice_id_unique"),
    ("Payment", "id", "payment_id_unique"),
    ("Expense", "id", "expense_id_unique"),
    ("Vendor", "name", "vendor_name_unique")
]

for label, prop, name in constraints:
    c_query = f"CREATE CONSTRAINT {name} IF NOT EXISTS FOR (n:{label}) REQUIRE n.{prop} IS UNIQUE"
    run_cypher(c_query)

print("  ✓ Đã thiết lập 7 Constraints & Indexes trên các trường khóa chính.")

# -------------------------------------------------------------
# 3. LOAD DIM_DEPARTMENTS & DIM_MAJORS
# -------------------------------------------------------------
print("\n[Bước 2/7] Nạp Danh mục Khoa & Chuyên ngành...")
df_dept = pd.read_csv(os.path.join(CLEAN_DIR, "dim_departments.csv"), encoding="utf-8-sig")
dept_records = df_dept.fillna("").to_dict(orient="records")

cypher_dept = """
UNWIND $batch AS row
MERGE (d:Department {id: row.Department_ID})
SET d.name = row.Department_Name,
    d.faculty = row.Faculty_Name,
    d.manager = row.Manager_Name,
    d.annual_budget = toInteger(row.Annual_Budget),
    d.created_date = date(row.Created_Date)
"""
batch_insert(cypher_dept, dept_records, desc="Nodes :Department")

# -------------------------------------------------------------
# 4. LOAD DIM_STUDENTS & ML RISK FEATURES
# -------------------------------------------------------------
print("\n[Bước 3/7] Nạp Danh mục Sinh viên & Đặc trưng rủi ro ML...")
df_students = pd.read_csv(os.path.join(CLEAN_DIR, "dim_students.csv"), encoding="utf-8-sig")
df_ml_student = pd.read_csv(os.path.join(ML_DIR, "ml_student_finance_features.csv"), encoding="utf-8-sig")

# Merge student info with ML features (debt, risk score, target labels)
ml_cols = ['Student_ID', 'total_invoices_count', 'total_tuition_billed', 'total_tuition_paid', 
           'total_remaining_debt', 'payment_completion_rate', 'failed_payments_count', 
           'payment_failure_rate', 'target_high_debt_risk', 'target_is_dropped_out']
df_merged_students = df_students.merge(df_ml_student[ml_cols], on='Student_ID', how='left')

# Calculate composite risk score
df_merged_students['risk_score'] = (
    (1.0 - df_merged_students['payment_completion_rate'].fillna(1.0)) * 40.0 +
    df_merged_students['payment_failure_rate'].fillna(0.0) * 30.0 +
    df_merged_students['total_remaining_debt'].apply(lambda x: 20.0 if x > 15000000 else (10.0 if x > 0 else 0.0)) +
    df_merged_students['Status'].apply(lambda s: 10.0 if s in ['Suspended', 'Dropped Out'] else 0.0)
).round(1)

student_records = df_merged_students.fillna("").to_dict(orient="records")

cypher_students = """
UNWIND $batch AS row
MERGE (s:Student {id: row.Student_ID})
SET s.full_name = row.Full_Name,
    s.date_of_birth = date(row.Date_Of_Birth),
    s.gender = row.Gender,
    s.email = row.Email,
    s.phone = row.Phone,
    s.enrollment_date = date(row.Enrollment_Date),
    s.status = row.Status,
    s.dropout_date = CASE WHEN row.Dropout_Date <> '' THEN date(row.Dropout_Date) ELSE null END,
    s.total_tuition_billed = toInteger(row.total_tuition_billed),
    s.total_tuition_paid = toInteger(row.total_tuition_paid),
    s.total_remaining_debt = toInteger(row.total_remaining_debt),
    s.payment_completion_rate = toFloat(row.payment_completion_rate),
    s.failed_payments_count = toInteger(row.failed_payments_count),
    s.risk_score = toFloat(row.risk_score),
    s.is_high_debt_risk = (row.target_high_debt_risk = 1)
WITH s, row
MERGE (d:Department {id: row.Department_ID})
MERGE (s)-[:BELONGS_TO]->(d)
WITH s, row, d
MERGE (m:Major {name: row.Major})
MERGE (s)-[:STUDIES]->(m)
MERGE (m)-[:OFFERED_BY]->(d)
"""
batch_insert(cypher_students, student_records, batch_size=300, desc="Nodes :Student, :Major & Relationships [:BELONGS_TO], [:STUDIES], [:OFFERED_BY]")

# -------------------------------------------------------------
# 5. LOAD FACT_TUITION_INVOICES
# -------------------------------------------------------------
print("\n[Bước 4/7] Nạp Hóa đơn học phí...")
df_invoices = pd.read_csv(os.path.join(CLEAN_DIR, "fact_tuition_invoices.csv"), encoding="utf-8-sig")
invoice_records = df_invoices.fillna("").to_dict(orient="records")

cypher_invoices = """
UNWIND $batch AS row
MERGE (i:Invoice {id: row.Invoice_ID})
SET i.semester = row.Semester,
    i.academic_year = row.Academic_Year,
    i.invoice_date = date(row.Invoice_Date),
    i.due_date = date(row.Due_Date),
    i.tuition_fee = toInteger(row.Tuition_Fee),
    i.scholarship_amount = toInteger(row.Scholarship_Amount),
    i.late_fee = toInteger(row.Late_Fee),
    i.total_amount = toInteger(row.Total_Amount),
    i.total_paid_successful = toInteger(row.Total_Paid_Successful),
    i.remaining_balance = toInteger(row.Remaining_Balance),
    i.status = row.Calculated_Invoice_Status
WITH i, row
MERGE (s:Student {id: row.Student_ID})
MERGE (i)-[:BILLED_TO]->(s)
"""
batch_insert(cypher_invoices, invoice_records, batch_size=500, desc="Nodes :Invoice & Relationships [:BILLED_TO]")

# -------------------------------------------------------------
# 6. LOAD FACT_PAYMENTS
# -------------------------------------------------------------
print("\n[Bước 5/7] Nạp Giao dịch thanh toán...")
df_payments = pd.read_csv(os.path.join(CLEAN_DIR, "fact_payments.csv"), encoding="utf-8-sig")
payment_records = df_payments.fillna("").to_dict(orient="records")

cypher_payments = """
UNWIND $batch AS row
MERGE (p:Payment {id: row.Payment_ID})
SET p.payment_date = date(row.Payment_Date),
    p.payment_method = row.Payment_Method,
    p.amount_paid = toInteger(row.Amount_Paid),
    p.transaction_ref = row.Transaction_Reference,
    p.payment_status = row.Payment_Status
WITH p, row
MERGE (i:Invoice {id: row.Invoice_ID})
MERGE (p)-[:SETTLES]->(i)
WITH p, row
MERGE (s:Student {id: row.Student_ID})
MERGE (p)-[:MADE_BY]->(s)
"""
batch_insert(cypher_payments, payment_records, batch_size=500, desc="Nodes :Payment & Relationships [:SETTLES], [:MADE_BY]")

# -------------------------------------------------------------
# 7. LOAD FACT_EXPENSES & VENDORS
# -------------------------------------------------------------
print("\n[Bước 6/7] Nạp Chi phí hoạt động & Nhà cung cấp...")
df_expenses = pd.read_csv(os.path.join(CLEAN_DIR, "fact_expenses.csv"), encoding="utf-8-sig")
expense_records = df_expenses.fillna("").to_dict(orient="records")

cypher_expenses = """
UNWIND $batch AS row
MERGE (e:Expense {id: row.Expense_ID})
SET e.expense_date = date(row.Expense_Date),
    e.category = row.Expense_Category,
    e.description = row.Description,
    e.amount = toInteger(row.Amount),
    e.approval_status = row.Approval_Status,
    e.payment_method = row.Payment_Method
WITH e, row
MERGE (d:Department {id: row.Department_ID})
MERGE (e)-[:INCURRED_BY]->(d)
WITH e, row
MERGE (v:Vendor {name: row.Vendor_Name})
MERGE (e)-[:PAID_TO]->(v)
"""
batch_insert(cypher_expenses, expense_records, batch_size=500, desc="Nodes :Expense, :Vendor & Relationships [:INCURRED_BY], [:PAID_TO]")

# -------------------------------------------------------------
# 8. LOAD DATA QUALITY AUDIT MANIFEST
# -------------------------------------------------------------
print("\n[Bước 7/7] Nạp Nhật ký kiểm soát chất lượng dữ liệu (Audit Manifest)...")
df_manifest = pd.read_csv(os.path.join(RAW_DIR, "data_quality_manifest.csv"), encoding="utf-8-sig")
manifest_records = df_manifest.fillna("").to_dict(orient="records")

cypher_audit = """
UNWIND $batch AS row
CREATE (a:DataQualityAudit {
    record_id: row.Record_ID,
    table_name: row.Table_Name,
    error_type: row.Error_Type,
    column_name: row.Column_Name,
    original_value: toString(row.Original_Value),
    corrupted_value: toString(row.Corrupted_Value),
    description: row.Description
})
"""
batch_insert(cypher_audit, manifest_records, batch_size=500, desc="Nodes :DataQualityAudit")

# -------------------------------------------------------------
# 9. VERIFY FINAL GRAPH STATISTICS
# -------------------------------------------------------------
print("\n" + "=" * 70)
print("📊 KIỂM TRA THỐNG KÊ ĐỒ THỊ SAU KHI NẠP:")
print("=" * 70)

with driver.session() as session:
    # Count Nodes
    node_counts = session.run("""
    MATCH (n)
    RETURN labels(n)[0] AS Label, count(n) AS SoLuong
    ORDER BY SoLuong DESC
    """).data()
    
    print("\n📦 CÁC LOẠI NODE (THỰC THỂ):")
    for r in node_counts:
        print(f"  • :{r['Label']:<20} : {r['SoLuong']:,} nodes")

    # Count Relationships
    rel_counts = session.run("""
    MATCH ()-[r]->()
    RETURN type(r) AS Relationship, count(r) AS SoLuong
    ORDER BY SoLuong DESC
    """).data()
    
    print("\n🔗 CÁC LOẠI RELATIONSHIP (MỐI QUAN HỆ):")
    for r in rel_counts:
        print(f"  • [:{r['Relationship']:<18}] : {r['SoLuong']:,} links")

driver.close()

print("\n" + "=" * 70)
print("🎉 BƯỚC 7 ĐÃ HOÀN THÀNH XUẤT SẮC! TOÀN BỘ DỮ LIỆU ĐÃ SẴN SÀNG TRONG NEO4J!")
print("=" * 70)
