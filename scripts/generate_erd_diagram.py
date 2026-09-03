"""
Generate Schema & Entity-Relationship Diagrams (ERD) with all 6 tables (including data_quality_manifest audit table).
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

PROJECT_ROOT = os.path.abspath("d:/NHG/AgentofMRP")
FIG_DIR = os.path.join(PROJECT_ROOT, "reports", "figures")
os.makedirs(FIG_DIR, exist_ok=True)

fig, ax = plt.subplots(figsize=(16, 11), dpi=300)
ax.set_xlim(0, 160)
ax.set_ylim(0, 110)
ax.axis('off')

# Title
ax.text(80, 106, "TOÀN BỘ 6 BẢNG DỮ LIỆU: ERD & AUDIT LOG METADATA SCHEMA", 
        ha='center', va='center', fontsize=16, fontweight='bold', color='#0f172a')
ax.text(80, 102.5, "5 Bảng Dữ Liệu Nghiệp Vụ (Star/Snowflake Schema) + 1 Bảng Nhật Ký Lỗi & Kiểm Soát Chất Lượng (Audit Manifest)", 
        ha='center', va='center', fontsize=10.5, color='#64748b')

# Helper to draw table box
def draw_table(ax, x, y, width, height, title, fields, bg_color='#ffffff', header_color='#1e293b'):
    # Header
    hdr_box = FancyBboxPatch((x, y + height - 5), width, 5, boxstyle="round,pad=0.2,rounding_size=1",
                             facecolor=header_color, edgecolor='#0f172a', linewidth=1.2)
    ax.add_patch(hdr_box)
    ax.text(x + width/2, y + height - 2.5, title, ha='center', va='center', 
            fontsize=9.5, fontweight='bold', color='#ffffff')
    
    # Body
    body_box = FancyBboxPatch((x, y), width, height - 5, boxstyle="round,pad=0.2,rounding_size=1",
                              facecolor=bg_color, edgecolor='#cbd5e1', linewidth=1.1)
    ax.add_patch(body_box)
    
    line_y = y + height - 8
    for f_pk_fk, f_name, f_type in fields:
        if f_pk_fk:
            badge_color = '#ef4444' if 'PK' in f_pk_fk else ('#f59e0b' if 'FK' in f_pk_fk else '#3b82f6')
            ax.text(x + 1.5, line_y, f_pk_fk, ha='left', va='center', 
                    fontsize=7, fontweight='bold', color=badge_color)
        ax.text(x + 8, line_y, f_name, ha='left', va='center', 
                fontsize=8, color='#1e293b', fontweight='semibold' if f_pk_fk else 'normal')
        ax.text(x + width - 1.5, line_y, f_type, ha='right', va='center', 
                fontsize=7, color='#64748b', style='italic')
        line_y -= 3.0

# 1. dim_departments (Top-Left)
dept_fields = [
    ("[PK]", "Department_ID", "VARCHAR"),
    ("", "Department_Name", "NVARCHAR"),
    ("", "Faculty_Name", "NVARCHAR"),
    ("", "Manager_Name", "NVARCHAR"),
    ("", "Annual_Budget", "BIGINT"),
    ("", "Created_Date", "DATE")
]
draw_table(ax, 8, 68, 34, 25, "1. dim_departments (20)", dept_fields, header_color='#0d9488')

# 2. dim_students (Center-Top)
stu_fields = [
    ("[PK]", "Student_ID", "VARCHAR"),
    ("", "Full_Name", "NVARCHAR"),
    ("", "Date_Of_Birth", "DATE"),
    ("", "Gender", "ENUM"),
    ("", "Email", "VARCHAR"),
    ("", "Phone", "VARCHAR"),
    ("[FK]", "Department_ID", "VARCHAR"),
    ("", "Major", "NVARCHAR"),
    ("", "Enrollment_Date", "DATE"),
    ("", "Status", "ENUM"),
    ("", "Dropout_Date", "DATE NULL")
]
draw_table(ax, 48, 58, 35, 40, "2. dim_students (1,490)", stu_fields, header_color='#0284c7')

# 3. fact_tuition_invoices (Center-Right)
inv_fields = [
    ("[PK]", "Invoice_ID", "VARCHAR"),
    ("[FK]", "Student_ID", "VARCHAR"),
    ("", "Semester", "ENUM"),
    ("", "Academic_Year", "CHAR(9)"),
    ("", "Invoice_Date", "DATE"),
    ("", "Due_Date", "DATE"),
    ("", "Tuition_Fee", "BIGINT"),
    ("", "Scholarship_Amount", "BIGINT"),
    ("", "Late_Fee", "BIGINT"),
    ("", "Total_Amount", "BIGINT"),
    ("", "Calculated_Status", "ENUM"),
    ("", "Remaining_Balance", "BIGINT")
]
draw_table(ax, 89, 54, 35, 44, "3. fact_tuition_invoices (2,985)", inv_fields, header_color='#7c3aed')

# 4. fact_payments (Far-Right)
pay_fields = [
    ("[PK]", "Payment_ID", "VARCHAR"),
    ("[FK]", "Invoice_ID", "VARCHAR"),
    ("[FK]", "Student_ID", "VARCHAR"),
    ("", "Payment_Date", "DATE"),
    ("", "Payment_Method", "ENUM"),
    ("", "Amount_Paid", "BIGINT"),
    ("", "Transaction_Ref", "VARCHAR"),
    ("", "Payment_Status", "ENUM")
]
draw_table(ax, 128, 54, 30, 36, "4. fact_payments (3,500)", pay_fields, header_color='#ea580c')

# 5. fact_expenses (Bottom-Left)
exp_fields = [
    ("[PK]", "Expense_ID", "VARCHAR"),
    ("[FK]", "Department_ID", "VARCHAR"),
    ("", "Expense_Date", "DATE"),
    ("", "Expense_Category", "ENUM"),
    ("", "Vendor_Name", "NVARCHAR"),
    ("", "Description", "NVARCHAR"),
    ("", "Amount", "BIGINT"),
    ("", "Approval_Status", "ENUM"),
    ("", "Payment_Method", "ENUM")
]
draw_table(ax, 8, 14, 34, 38, "5. fact_expenses (1,985)", exp_fields, header_color='#e11d48')

# 6. data_quality_manifest (Bottom-Center/Right) - The Audit Log Table
manifest_fields = [
    ("[REF]", "Table_Name", "VARCHAR"),
    ("[REF]", "Record_ID", "VARCHAR"),
    ("", "Error_Type", "VARCHAR"),
    ("", "Column_Name", "VARCHAR"),
    ("", "Original_Value", "TEXT"),
    ("", "Corrupted_Value", "TEXT"),
    ("", "Description", "TEXT")
]
draw_table(ax, 52, 14, 72, 32, "6. data_quality_manifest (1,086 - Audit/Log)", manifest_fields, 
           bg_color='#fffbeb', header_color='#b45309')

# Connectors for Business Relationships
# dim_departments -> dim_students
ax.annotate("", xy=(48, 78), xytext=(42, 78), arrowprops=dict(arrowstyle="-|>", color="#0d9488", lw=2))
ax.text(43.5, 80, "1:N", fontsize=8, fontweight='bold', color="#0d9488")

# dim_departments -> fact_expenses
ax.annotate("", xy=(25, 52), xytext=(25, 68), arrowprops=dict(arrowstyle="-|>", color="#0d9488", lw=2))
ax.text(26, 60, "1:N", fontsize=8, fontweight='bold', color="#0d9488")

# dim_students -> fact_tuition_invoices
ax.annotate("", xy=(89, 78), xytext=(83, 78), arrowprops=dict(arrowstyle="-|>", color="#0284c7", lw=2))
ax.text(84.5, 80, "1:N", fontsize=8, fontweight='bold', color="#0284c7")

# fact_tuition_invoices -> fact_payments
ax.annotate("", xy=(128, 72), xytext=(124, 72), arrowprops=dict(arrowstyle="-|>", color="#7c3aed", lw=2))
ax.text(124.5, 74, "1:N", fontsize=8, fontweight='bold', color="#7c3aed")

# Audit Trace Connectors from data_quality_manifest to Business Tables (Dashed lines)
ax.annotate("", xy=(25, 14), xytext=(52, 28), arrowprops=dict(arrowstyle="->", color="#b45309", lw=1.2, ls="--"))
ax.text(32, 20, "Audit Trace", fontsize=7.5, color="#b45309", style="italic")

ax.annotate("", xy=(65, 58), xytext=(70, 46), arrowprops=dict(arrowstyle="->", color="#b45309", lw=1.2, ls="--"))
ax.text(68, 51, "Audit Trace", fontsize=7.5, color="#b45309", style="italic")

ax.annotate("", xy=(106, 54), xytext=(98, 46), arrowprops=dict(arrowstyle="->", color="#b45309", lw=1.2, ls="--"))
ax.text(103, 49, "Audit Trace", fontsize=7.5, color="#b45309", style="italic")

ax.annotate("", xy=(135, 54), xytext=(120, 42), arrowprops=dict(arrowstyle="->", color="#b45309", lw=1.2, ls="--"))
ax.text(128, 47, "Audit Trace", fontsize=7.5, color="#b45309", style="italic")

plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "dataset_entity_relationship_diagram.png"), dpi=300)
plt.close(fig)

print("Updated 6-table ERD diagram at reports/figures/dataset_entity_relationship_diagram.png")
