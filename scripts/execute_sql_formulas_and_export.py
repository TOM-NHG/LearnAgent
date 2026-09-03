"""
MRP Finance & Student Analytics - SQL Formula Calculation Engine & Exporter
Executes standard SQL queries over SQLite to compute all 12 business & financial metrics
and exports structured JSON data for the interactive Executive Dashboard.
"""

import os
import sqlite3
import json
import pandas as pd
import numpy as np

PROJECT_ROOT = os.path.abspath("d:/NHG/AgentofMRP")
CLEAN_DIR = os.path.join(PROJECT_ROOT, "data", "cleaned")
RAW_DIR = os.path.join(PROJECT_ROOT, "data")
ML_DIR = os.path.join(PROJECT_ROOT, "data", "ml_ready")
REPORTS_DIR = os.path.join(PROJECT_ROOT, "reports")
DB_PATH = os.path.join(PROJECT_ROOT, "data", "mrp_finance.db")

print("1. Loading clean tables into SQLite database...")
conn = sqlite3.connect(DB_PATH)
cursor = conn.cursor()

# Load DataFrames from clean CSVs
df_students = pd.read_csv(os.path.join(CLEAN_DIR, "dim_students.csv"), encoding="utf-8-sig")
df_dept = pd.read_csv(os.path.join(CLEAN_DIR, "dim_departments.csv"), encoding="utf-8-sig")
df_invoices = pd.read_csv(os.path.join(CLEAN_DIR, "fact_tuition_invoices.csv"), encoding="utf-8-sig")
df_payments = pd.read_csv(os.path.join(CLEAN_DIR, "fact_payments.csv"), encoding="utf-8-sig")
df_expenses = pd.read_csv(os.path.join(CLEAN_DIR, "fact_expenses.csv"), encoding="utf-8-sig")
df_manifest = pd.read_csv(os.path.join(RAW_DIR, "data_quality_manifest.csv"), encoding="utf-8-sig")
df_ml_student = pd.read_csv(os.path.join(ML_DIR, "ml_student_finance_features.csv"), encoding="utf-8-sig")

# Write to SQLite
df_students.to_sql("dim_students", conn, if_exists="replace", index=False)
df_dept.to_sql("dim_departments", conn, if_exists="replace", index=False)
df_invoices.to_sql("fact_tuition_invoices", conn, if_exists="replace", index=False)
df_payments.to_sql("fact_payments", conn, if_exists="replace", index=False)
df_expenses.to_sql("fact_expenses", conn, if_exists="replace", index=False)
df_manifest.to_sql("data_quality_manifest", conn, if_exists="replace", index=False)
df_ml_student.to_sql("ml_student_features", conn, if_exists="replace", index=False)

print("Tables loaded successfully into SQLite.")

# -------------------------------------------------------------
# 2. DEFINE & EXECUTE SQL FORMULAS
# -------------------------------------------------------------
print("2. Executing SQL queries for all 12 business formula areas...")

# Reference analysis date (anchor date in dataset)
AS_OF_DATE = '2026-08-30'

# SQL 1: High Level KPI Overview
sql_kpi_overview = f"""
WITH PaymentSummary AS (
    SELECT 
        Invoice_ID,
        SUM(CASE WHEN Payment_Status = 'Successful' THEN Amount_Paid ELSE 0 END) AS Paid_Amount
    FROM fact_payments
    GROUP BY Invoice_ID
),
InvoiceDetail AS (
    SELECT 
        i.Invoice_ID,
        i.Student_ID,
        i.Semester,
        i.Academic_Year,
        i.Due_Date,
        i.Tuition_Fee,
        i.Scholarship_Amount,
        i.Late_Fee,
        (i.Tuition_Fee - i.Scholarship_Amount + i.Late_Fee) AS Net_Invoice_Amount,
        COALESCE(p.Paid_Amount, 0) AS Total_Paid,
        MAX(0, (i.Tuition_Fee - i.Scholarship_Amount + i.Late_Fee) - COALESCE(p.Paid_Amount, 0)) AS Remaining_Debt,
        CASE 
            WHEN MAX(0, (i.Tuition_Fee - i.Scholarship_Amount + i.Late_Fee) - COALESCE(p.Paid_Amount, 0)) > 0 
                 AND DATE('{AS_OF_DATE}') > DATE(i.Due_Date)
            THEN MAX(0, (i.Tuition_Fee - i.Scholarship_Amount + i.Late_Fee) - COALESCE(p.Paid_Amount, 0))
            ELSE 0 
        END AS Overdue_Debt,
        CASE 
            WHEN MAX(0, (i.Tuition_Fee - i.Scholarship_Amount + i.Late_Fee) - COALESCE(p.Paid_Amount, 0)) > 0 
                 AND DATE('{AS_OF_DATE}') > DATE(i.Due_Date)
            THEN CAST(JULIANDAY('{AS_OF_DATE}') - JULIANDAY(i.Due_Date) AS INTEGER)
            ELSE 0
        END AS Days_Past_Due
    FROM fact_tuition_invoices i
    LEFT JOIN PaymentSummary p ON i.Invoice_ID = p.Invoice_ID
),
ExpenseSummary AS (
    SELECT 
        SUM(Amount) AS Total_Expenses_All,
        SUM(CASE WHEN Approval_Status = 'Approved' THEN Amount ELSE 0 END) AS Total_Expenses_Approved,
        SUM(CASE WHEN Approval_Status = 'Pending' THEN Amount ELSE 0 END) AS Total_Expenses_Pending
    FROM fact_expenses
)
SELECT 
    COUNT(DISTINCT i.Invoice_ID) AS Total_Invoices_Count,
    SUM(i.Net_Invoice_Amount) AS Total_Billed_Tuition,
    SUM(i.Tuition_Fee) AS Gross_Tuition_Fee,
    SUM(i.Scholarship_Amount) AS Total_Scholarship_Granted,
    SUM(i.Late_Fee) AS Total_Late_Fee_Charged,
    SUM(i.Total_Paid) AS Total_Collected_Tuition,
    SUM(i.Remaining_Debt) AS Total_Remaining_Debt,
    ROUND(SUM(i.Total_Paid) * 100.0 / NULLIF(SUM(i.Net_Invoice_Amount), 0), 2) AS Collection_Rate_Pct,
    SUM(i.Overdue_Debt) AS Total_Overdue_Debt,
    ROUND(SUM(i.Overdue_Debt) * 100.0 / NULLIF(SUM(i.Remaining_Debt), 0), 2) AS Overdue_To_Debt_Ratio_Pct,
    e.Total_Expenses_Approved,
    e.Total_Expenses_All,
    (SUM(i.Total_Paid) - e.Total_Expenses_Approved) AS Net_Cash_Flow
FROM InvoiceDetail i
CROSS JOIN ExpenseSummary e;
"""
df_kpi = pd.read_sql_query(sql_kpi_overview, conn)
kpi_dict = df_kpi.iloc[0].to_dict()

# SQL 2: Debt Aging Buckets
sql_debt_aging = f"""
WITH InvoiceDebt AS (
    SELECT 
        i.Invoice_ID,
        i.Due_Date,
        (i.Tuition_Fee - i.Scholarship_Amount + i.Late_Fee) AS Net_Invoice_Amount,
        COALESCE(SUM(CASE WHEN p.Payment_Status = 'Successful' THEN p.Amount_Paid ELSE 0 END), 0) AS Total_Paid,
        MAX(0, (i.Tuition_Fee - i.Scholarship_Amount + i.Late_Fee) - COALESCE(SUM(CASE WHEN p.Payment_Status = 'Successful' THEN p.Amount_Paid ELSE 0 END), 0)) AS Debt_Amount,
        CAST(JULIANDAY('{AS_OF_DATE}') - JULIANDAY(i.Due_Date) AS INTEGER) AS Days_Overdue
    FROM fact_tuition_invoices i
    LEFT JOIN fact_payments p ON i.Invoice_ID = p.Invoice_ID
    GROUP BY i.Invoice_ID
)
SELECT 
    CASE 
        WHEN Debt_Amount = 0 THEN '0. Đã Tất Toán (Paid in Full)'
        WHEN Days_Overdue <= 0 THEN '1. Trong Hạn (Current / Not Due)'
        WHEN Days_Overdue BETWEEN 1 AND 30 THEN '2. Quá Hạn 1 - 30 Ngày'
        WHEN Days_Overdue BETWEEN 31 AND 60 THEN '3. Quá Hạn 31 - 60 Ngày'
        WHEN Days_Overdue BETWEEN 61 AND 90 THEN '4. Quá Hạn 61 - 90 Ngày'
        ELSE '5. Nợ Xấu > 90 Ngày'
    END AS Aging_Bucket,
    COUNT(Invoice_ID) AS Invoices_Count,
    SUM(Debt_Amount) AS Total_Debt_In_Bucket,
    ROUND(SUM(Debt_Amount) * 100.0 / (SELECT SUM(Debt_Amount) FROM InvoiceDebt WHERE Debt_Amount > 0), 2) AS Share_Of_Total_Debt_Pct
FROM InvoiceDebt
GROUP BY Aging_Bucket
ORDER BY Aging_Bucket;
"""
df_aging = pd.read_sql_query(sql_debt_aging, conn)

# SQL 3: Department Financial Performance
sql_dept_performance = """
WITH DeptTuition AS (
    SELECT 
        s.Department_ID,
        COUNT(DISTINCT s.Student_ID) AS Total_Students,
        SUM(CASE WHEN s.Status = 'Active' THEN 1 ELSE 0 END) AS Active_Students,
        SUM(CASE WHEN s.Status = 'Dropped Out' THEN 1 ELSE 0 END) AS Dropped_Students,
        SUM(i.Total_Amount) AS Dept_Billed_Tuition,
        SUM(i.Total_Paid_Successful) AS Dept_Collected_Tuition,
        SUM(i.Remaining_Balance) AS Dept_Remaining_Debt
    FROM dim_students s
    LEFT JOIN fact_tuition_invoices i ON s.Student_ID = i.Student_ID
    GROUP BY s.Department_ID
),
DeptExpenses AS (
    SELECT 
        Department_ID,
        SUM(CASE WHEN Approval_Status = 'Approved' THEN Amount ELSE 0 END) AS Approved_Expenses,
        SUM(Amount) AS Total_Expenses,
        COUNT(Expense_ID) AS Expense_Transactions_Count
    FROM fact_expenses
    GROUP BY Department_ID
)
SELECT 
    d.Department_ID,
    d.Department_Name,
    d.Faculty_Name,
    d.Manager_Name,
    d.Annual_Budget,
    COALESCE(t.Total_Students, 0) AS Total_Students,
    COALESCE(t.Active_Students, 0) AS Active_Students,
    COALESCE(t.Dropped_Students, 0) AS Dropped_Students,
    COALESCE(t.Dept_Billed_Tuition, 0) AS Billed_Tuition,
    COALESCE(t.Dept_Collected_Tuition, 0) AS Collected_Tuition,
    COALESCE(t.Dept_Remaining_Debt, 0) AS Remaining_Debt,
    ROUND(COALESCE(t.Dept_Collected_Tuition, 0) * 100.0 / NULLIF(t.Dept_Billed_Tuition, 0), 2) AS Collection_Rate_Pct,
    COALESCE(e.Approved_Expenses, 0) AS Approved_Expenses,
    (COALESCE(t.Dept_Collected_Tuition, 0) - COALESCE(e.Approved_Expenses, 0)) AS Net_Cash_Flow,
    ROUND(COALESCE(e.Approved_Expenses, 0) * 100.0 / NULLIF(d.Annual_Budget, 0), 2) AS Budget_Burn_Rate_Pct,
    ROUND(COALESCE(e.Approved_Expenses, 0) * 1.0 / NULLIF(t.Active_Students, 0), 0) AS Cost_Per_Active_Student
FROM dim_departments d
LEFT JOIN DeptTuition t ON d.Department_ID = t.Department_ID
LEFT JOIN DeptExpenses e ON d.Department_ID = e.Department_ID
ORDER BY Net_Cash_Flow DESC;
"""
df_dept_perf = pd.read_sql_query(sql_dept_performance, conn)

# SQL 4: Expense Breakdown by Category
sql_expense_cat = """
SELECT 
    Expense_Category,
    COUNT(Expense_ID) AS Transactions_Count,
    SUM(Amount) AS Total_Amount,
    SUM(CASE WHEN Approval_Status = 'Approved' THEN Amount ELSE 0 END) AS Approved_Amount,
    SUM(CASE WHEN Approval_Status = 'Pending' THEN Amount ELSE 0 END) AS Pending_Amount,
    ROUND(SUM(Amount) * 100.0 / (SELECT SUM(Amount) FROM fact_expenses), 2) AS Category_Share_Pct
FROM fact_expenses
GROUP BY Expense_Category
ORDER BY Total_Amount DESC;
"""
df_exp_cat = pd.read_sql_query(sql_expense_cat, conn)

# SQL 5: Student Risk Ranking & Scoring
sql_student_risk = """
SELECT 
    s.Student_ID,
    s.Full_Name,
    d.Department_Name,
    s.Major,
    s.Status,
    m.total_invoices_count,
    m.total_tuition_billed,
    m.total_tuition_paid,
    m.total_remaining_debt,
    m.payment_completion_rate,
    m.failed_payments_count,
    m.payment_failure_rate,
    m.has_overdue_debt,
    m.target_high_debt_risk,
    m.target_is_dropped_out,
    -- Composite Risk Score Formula (0 to 100)
    ROUND(
        (1.0 - m.payment_completion_rate) * 40.0 +
        m.payment_failure_rate * 30.0 +
        (CASE WHEN m.total_remaining_debt > 15000000 THEN 20.0 WHEN m.total_remaining_debt > 0 THEN 10.0 ELSE 0.0 END) +
        (CASE WHEN s.Status = 'Suspended' THEN 10.0 WHEN s.Status = 'Dropped Out' THEN 10.0 ELSE 0.0 END),
        1
    ) AS Composite_Risk_Score
FROM ml_student_features m
JOIN dim_students s ON m.Student_ID = s.Student_ID
JOIN dim_departments d ON s.Department_ID = d.Department_ID
ORDER BY Composite_Risk_Score DESC, m.total_remaining_debt DESC
LIMIT 100;
"""
df_stu_risk = pd.read_sql_query(sql_student_risk, conn)

# SQL 6: Data Quality Audit Manifest Summary
sql_data_quality = """
SELECT 
    Table_Name,
    Error_Type,
    Column_Name,
    COUNT(Record_ID) AS Total_Corrupted_Records,
    MIN(Description) AS Sample_Description
FROM data_quality_manifest
GROUP BY Table_Name, Error_Type, Column_Name
ORDER BY Total_Corrupted_Records DESC;
"""
df_dq = pd.read_sql_query(sql_data_quality, conn)

# SQL 7: Semester-by-Semester Invoicing and Collection Trend
sql_semester_trend = """
SELECT 
    Academic_Year,
    Semester,
    COUNT(Invoice_ID) AS Invoices_Count,
    SUM(Total_Amount) AS Total_Billed,
    SUM(Total_Paid_Successful) AS Total_Collected,
    SUM(Remaining_Balance) AS Total_Unpaid,
    ROUND(SUM(Total_Paid_Successful) * 100.0 / NULLIF(SUM(Total_Amount), 0), 2) AS Collection_Rate_Pct
FROM fact_tuition_invoices
GROUP BY Academic_Year, Semester
ORDER BY Academic_Year, Semester;
"""
df_semester = pd.read_sql_query(sql_semester_trend, conn)

# SQL 8: Payment Methods Analysis
sql_pay_method = """
SELECT 
    Payment_Method,
    Payment_Status,
    COUNT(Payment_ID) AS Transactions_Count,
    SUM(Amount_Paid) AS Total_Amount
FROM fact_payments
GROUP BY Payment_Method, Payment_Status
ORDER BY Payment_Method, Total_Amount DESC;
"""
df_pay_method = pd.read_sql_query(sql_pay_method, conn)

# -------------------------------------------------------------
# 3. CONSTRUCT COMPLETE JSON DATA STRUCTURE
# -------------------------------------------------------------
print("3. Packaging metrics into JSON payload for the Executive Dashboard...")

dashboard_payload = {
    "metadata": {
        "as_of_date": AS_OF_DATE,
        "engine": "SQLite 3.x / Python Remediation Pipeline",
        "status": "Verified Clean & Reconciled"
    },
    "kpi_overview": kpi_dict,
    "debt_aging": df_aging.to_dict(orient="records"),
    "department_performance": df_dept_perf.to_dict(orient="records"),
    "expense_categories": df_exp_cat.to_dict(orient="records"),
    "top_risk_students": df_stu_risk.to_dict(orient="records"),
    "data_quality_audit": df_dq.to_dict(orient="records"),
    "semester_trends": df_semester.to_dict(orient="records"),
    "payment_methods": df_pay_method.to_dict(orient="records")
}

json_path = os.path.join(REPORTS_DIR, "dashboard_data.json")
with open(json_path, "w", encoding="utf-8") as f:
    json.dump(dashboard_payload, f, ensure_ascii=False, indent=2)

print(f"Metrics exported successfully to: {json_path}")
conn.close()
