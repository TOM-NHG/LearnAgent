from __future__ import annotations

import json
import random
from pathlib import Path

import numpy as np
import pandas as pd
from faker import Faker


SEED = 20260828
OUTPUT_DIR = Path(__file__).resolve().parent / "output"
random.seed(SEED)
np.random.seed(SEED)
fake = Faker("vi_VN")
Faker.seed(SEED)

FINAL_ROWS = {
    "dim_students": 1500,
    "dim_departments": 20,
    "fact_tuition_invoices": 3000,
    "fact_payments": 3500,
    "fact_expenses": 2000,
}

DUPLICATES = {
    "dim_students": 10,
    "fact_tuition_invoices": 15,
    "fact_expenses": 15,
}

manifest: list[dict] = []


def record_error(table, record_id, error_type, column, original, corrupted, description):
    manifest.append(
        {
            "Table_Name": table,
            "Record_ID": record_id,
            "Error_Type": error_type,
            "Column_Name": column,
            "Original_Value": "" if pd.isna(original) else str(original),
            "Corrupted_Value": "" if pd.isna(corrupted) else str(corrupted),
            "Description": description,
        }
    )


def random_date(start="2019-01-01", end="2026-08-01"):
    start_ts, end_ts = pd.Timestamp(start), pd.Timestamp(end)
    return start_ts + pd.Timedelta(days=random.randint(0, (end_ts - start_ts).days))


def money(value):
    return int(round(value / 1000) * 1000)


def mixed_date_format(df, table, id_col, date_cols, rate=0.035):
    for col in date_cols:
        valid = df.index[df[col].notna()].tolist()
        chosen = random.sample(valid, min(round(len(df) * rate), len(valid)))
        # Force object dtype so pandas does not normalize DD/MM/YYYY back to Timestamp.
        df[col] = df[col].astype(object)
        for idx in valid:
            value = pd.Timestamp(df.at[idx, col])
            df.at[idx, col] = value.strftime("%Y-%m-%d")
        for idx in chosen:
            original = df.at[idx, col]
            corrupted = pd.Timestamp(original).strftime("%d/%m/%Y")
            df.at[idx, col] = corrupted
            record_error(table, df.at[idx, id_col], "MIXED_DATE_FORMAT", col, original, corrupted,
                         "Ngày được lưu theo DD/MM/YYYY thay vì YYYY-MM-DD.")


def dirty_text_format(df, table, id_col, col, rate=0.035):
    chosen = random.sample(df.index.tolist(), round(len(df) * rate))
    modes = ["upper", "lower", "spaces"]
    for idx in chosen:
        original = str(df.at[idx, col])
        mode = random.choice(modes)
        if mode == "upper":
            corrupted = original.upper()
        elif mode == "lower":
            corrupted = original.lower()
        else:
            corrupted = f"  {original}   "
        df.at[idx, col] = corrupted
        record_error(table, df.at[idx, id_col], "INCONSISTENT_TEXT_FORMAT", col, original, corrupted,
                     f"Chuỗi bị biến đổi kiểu {mode}.")


def add_exact_duplicates(df, table, id_col, count):
    copies = df.sample(n=count, random_state=SEED + len(df)).copy()
    for _, row in copies.iterrows():
        record_error(table, row[id_col], "EXACT_DUPLICATE_ROW", "ALL_COLUMNS", "unique row", "duplicated row",
                     "Toàn bộ bản ghi, bao gồm business key, bị ghi nhận hai lần.")
    return pd.concat([df, copies], ignore_index=True)


def build_departments():
    departments = [
        "Công nghệ thông tin", "Tài chính - Kế toán", "Quản trị kinh doanh", "Kinh tế",
        "Luật", "Ngoại ngữ", "Kỹ thuật điện", "Kỹ thuật xây dựng", "Công nghệ sinh học",
        "Du lịch - Khách sạn", "Truyền thông", "Khoa học dữ liệu", "Công tác sinh viên",
        "Đào tạo", "Khảo thí", "Cơ sở vật chất", "Nghiên cứu khoa học", "Thư viện",
        "Hợp tác quốc tế", "Hành chính - Nhân sự",
    ]
    rows = []
    for i, name in enumerate(departments, 1):
        rows.append({
            "Department_ID": f"DEP{i:03d}",
            "Department_Name": name,
            "Faculty_Name": f"Khối {name}" if i <= 12 else "Khối hành chính",
            "Manager_Name": fake.name(),
            "Annual_Budget": money(random.uniform(2_000_000_000, 20_000_000_000)),
            "Created_Date": random_date("2000-01-01", "2018-12-31"),
        })
    return pd.DataFrame(rows)


def build_students(departments):
    majors = departments.loc[:11, ["Department_ID", "Department_Name"]].set_index("Department_ID")["Department_Name"].to_dict()
    rows = []
    base_count = FINAL_ROWS["dim_students"] - DUPLICATES["dim_students"]
    for i in range(1, base_count + 1):
        dept_id = random.choice(list(majors))
        enrollment = random_date("2019-08-01", "2025-09-15")
        status = random.choices(["Active", "Graduated", "Suspended", "Dropped Out"], [62, 18, 7, 13])[0]
        dropout = None
        if status == "Dropped Out":
            dropout = enrollment + pd.Timedelta(days=random.randint(90, 900))
        rows.append({
            "Student_ID": f"STU{i:06d}", "Full_Name": fake.name(),
            "Date_Of_Birth": random_date("1998-01-01", "2007-12-31"),
            "Gender": random.choice(["Male", "Female", "Other"]),
            "Email": fake.unique.email(), "Phone": fake.phone_number(),
            "Department_ID": dept_id, "Major": majors[dept_id],
            "Enrollment_Date": enrollment, "Status": status, "Dropout_Date": dropout,
        })
    return pd.DataFrame(rows)


def build_invoices(students):
    rows = []
    base_count = FINAL_ROWS["fact_tuition_invoices"] - DUPLICATES["fact_tuition_invoices"]
    student_rows = students.drop_duplicates("Student_ID").set_index("Student_ID")
    ids = student_rows.index.tolist()
    for i in range(1, base_count + 1):
        sid = random.choice(ids)
        enroll = student_rows.at[sid, "Enrollment_Date"]
        invoice_date = enroll + pd.Timedelta(days=random.randint(0, 1800))
        tuition = money(random.uniform(8_000_000, 35_000_000))
        scholarship = money(tuition * random.choice([0, 0, 0, 0.1, 0.25, 0.5]))
        late_fee = money(random.choice([0, 0, 0, random.uniform(100_000, 1_500_000)]))
        total = tuition - scholarship + late_fee
        year = invoice_date.year
        semester = random.choice(["HK1", "HK2", "HK Hè"])
        rows.append({
            "Invoice_ID": f"INV{i:07d}", "Student_ID": sid, "Semester": semester,
            "Academic_Year": f"{year}-{year + 1}", "Invoice_Date": invoice_date,
            "Due_Date": invoice_date + pd.Timedelta(days=random.randint(20, 60)),
            "Tuition_Fee": tuition, "Scholarship_Amount": scholarship, "Late_Fee": late_fee,
            "Total_Amount": total, "Invoice_Status": random.choice(["Issued", "Partially Paid", "Paid", "Overdue"]),
        })
    return pd.DataFrame(rows)


def build_payments(invoices):
    rows = []
    clean_invoices = invoices.drop_duplicates("Invoice_ID").set_index("Invoice_ID")
    invoice_ids = clean_invoices.index.tolist()
    for i in range(1, FINAL_ROWS["fact_payments"] + 1):
        iid = random.choice(invoice_ids)
        inv = clean_invoices.loc[iid]
        amount = money(float(inv["Total_Amount"]) * random.uniform(0.25, 1.0))
        payment_date = inv["Invoice_Date"] + pd.Timedelta(days=random.randint(0, 100))
        status = random.choices(["Successful", "Pending", "Failed", "Reversed"], [86, 5, 6, 3])[0]
        rows.append({
            "Payment_ID": f"PAY{i:07d}", "Invoice_ID": iid, "Student_ID": inv["Student_ID"],
            "Payment_Date": payment_date, "Payment_Method": random.choice(["Bank Transfer", "Cash", "Card", "E-Wallet"]),
            "Amount_Paid": amount, "Transaction_Reference": fake.bothify("TXN-########??").upper(),
            "Payment_Status": status,
        })
    return pd.DataFrame(rows)


def build_expenses(departments):
    categories = {
        "Salary": (200_000_000, 1_000_000_000), "Equipment": (10_000_000, 400_000_000),
        "Maintenance": (3_000_000, 150_000_000), "Utilities": (5_000_000, 100_000_000),
        "Research": (20_000_000, 500_000_000), "Marketing": (5_000_000, 200_000_000),
        "Scholarship": (5_000_000, 300_000_000), "Office Supplies": (500_000, 30_000_000),
    }
    rows = []
    base_count = FINAL_ROWS["fact_expenses"] - DUPLICATES["fact_expenses"]
    dept_ids = departments["Department_ID"].tolist()
    for i in range(1, base_count + 1):
        category = random.choice(list(categories))
        low, high = categories[category]
        rows.append({
            "Expense_ID": f"EXP{i:07d}", "Department_ID": random.choice(dept_ids),
            "Expense_Date": random_date("2022-01-01", "2026-08-01"), "Expense_Category": category,
            "Vendor_Name": fake.company(), "Description": fake.sentence(nb_words=7),
            "Amount": money(random.uniform(low, high)),
            "Approval_Status": random.choice(["Approved", "Pending", "Rejected"]),
            "Payment_Method": random.choice(["Bank Transfer", "Cash", "Corporate Card"]),
        })
    return pd.DataFrame(rows)


def inject_errors(students, invoices, payments, expenses):
    # Missing Major: 3% students.
    for idx in random.sample(students.index.tolist(), round(len(students) * 0.03)):
        original = students.at[idx, "Major"]
        students.at[idx, "Major"] = None
        record_error("dim_students", students.at[idx, "Student_ID"], "MISSING_MAJOR", "Major", original, None,
                     "Sinh viên thiếu thông tin chuyên ngành.")

    # Missing Payment_Date: 2.5% payments.
    for idx in random.sample(payments.index.tolist(), round(len(payments) * 0.025)):
        original = payments.at[idx, "Payment_Date"]
        payments.at[idx, "Payment_Date"] = pd.NaT
        record_error("fact_payments", payments.at[idx, "Payment_ID"], "MISSING_PAYMENT_DATE", "Payment_Date", original, None,
                     "Giao dịch tồn tại nhưng ngày thanh toán bị null.")

    inv_lookup = invoices.drop_duplicates("Invoice_ID").set_index("Invoice_ID")
    eligible = payments.index[payments["Payment_Date"].notna()].tolist()

    # Payment before invoice: 2% payments.
    for idx in random.sample(eligible, round(len(payments) * 0.02)):
        invoice_date = inv_lookup.at[payments.at[idx, "Invoice_ID"], "Invoice_Date"]
        original = payments.at[idx, "Payment_Date"]
        corrupted = invoice_date - pd.Timedelta(days=random.randint(1, 60))
        payments.at[idx, "Payment_Date"] = corrupted
        record_error("fact_payments", payments.at[idx, "Payment_ID"], "PAYMENT_BEFORE_INVOICE", "Payment_Date", original, corrupted,
                     "Ngày đóng tiền sớm hơn ngày tạo hóa đơn.")

    # Overpayments: 2% payments.
    for idx in random.sample(payments.index.tolist(), round(len(payments) * 0.02)):
        total = float(inv_lookup.at[payments.at[idx, "Invoice_ID"], "Total_Amount"])
        original = payments.at[idx, "Amount_Paid"]
        corrupted = money(total * random.uniform(1.1, 3.0))
        payments.at[idx, "Amount_Paid"] = corrupted
        record_error("fact_payments", payments.at[idx, "Payment_ID"], "AMOUNT_PAID_EXCEEDS_INVOICE", "Amount_Paid", original, corrupted,
                     "Số tiền của một giao dịch lớn hơn tổng giá trị hóa đơn.")

    # Cross-table loophole: dropped-out students keep paying after Dropout_Date.
    dropped = students[students["Status"] == "Dropped Out"].drop_duplicates("Student_ID").set_index("Student_ID")
    candidates = payments.index[payments["Student_ID"].isin(dropped.index)].tolist()
    for idx in random.sample(candidates, min(60, len(candidates))):
        sid = payments.at[idx, "Student_ID"]
        dropout_date = dropped.at[sid, "Dropout_Date"]
        original = payments.at[idx, "Payment_Date"]
        corrupted = dropout_date + pd.Timedelta(days=random.randint(30, 500))
        payments.at[idx, "Payment_Date"] = corrupted
        record_error("fact_payments", payments.at[idx, "Payment_ID"], "PAYMENT_AFTER_DROPOUT", "Payment_Date", original, corrupted,
                     f"Sinh viên {sid} đã nghỉ học nhưng vẫn phát sinh thanh toán sau Dropout_Date.")

    # Formula mismatch in a small set of invoices, useful for the next Formula stage.
    for idx in random.sample(invoices.index.tolist(), 30):
        original = invoices.at[idx, "Total_Amount"]
        corrupted = original + money(random.uniform(200_000, 4_000_000))
        invoices.at[idx, "Total_Amount"] = corrupted
        record_error("fact_tuition_invoices", invoices.at[idx, "Invoice_ID"], "TOTAL_FORMULA_MISMATCH", "Total_Amount", original, corrupted,
                     "Total_Amount không bằng Tuition_Fee - Scholarship_Amount + Late_Fee.")

    # Extreme expenses: exactly four transactions from one department.
    target_department = random.choice(expenses["Department_ID"].unique().tolist())
    candidates = expenses.index[expenses["Department_ID"] == target_department].tolist()
    for idx in random.sample(candidates, min(4, len(candidates))):
        original = expenses.at[idx, "Amount"]
        corrupted = original * 100
        expenses.at[idx, "Amount"] = corrupted
        record_error("fact_expenses", expenses.at[idx, "Expense_ID"], "EXPENSE_OUTLIER_X100", "Amount", original, corrupted,
                     f"Khoản chi của {target_department} bị nhân 100 lần do lỗi nhập liệu.")


def validate_and_summarize(tables):
    summary = {
        "seed": SEED,
        "total_rows": int(sum(len(df) for df in tables.values())),
        "rows_per_table": {name: int(len(df)) for name, df in tables.items()},
        "manifest_events": len(manifest),
        "error_events_by_type": pd.Series([x["Error_Type"] for x in manifest]).value_counts().to_dict(),
        "quality_checks": {},
    }
    summary["quality_checks"]["all_target_row_counts_match"] = all(
        len(tables[name]) == count for name, count in FINAL_ROWS.items()
    )
    summary["quality_checks"]["student_duplicates_present"] = bool(tables["dim_students"].duplicated().any())
    summary["quality_checks"]["invoice_duplicates_present"] = bool(tables["fact_tuition_invoices"].duplicated().any())
    summary["quality_checks"]["expense_duplicates_present"] = bool(tables["fact_expenses"].duplicated().any())
    summary["quality_checks"]["missing_major_present"] = bool(tables["dim_students"]["Major"].isna().any())
    summary["quality_checks"]["missing_payment_date_present"] = bool(tables["fact_payments"]["Payment_Date"].isna().any())
    summary["quality_checks"]["mixed_date_formats_present"] = any(
        "/" in str(v) for v in tables["fact_payments"]["Payment_Date"].dropna()
    )
    return summary


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    departments = build_departments()
    students = build_students(departments)
    invoices = build_invoices(students)
    payments = build_payments(invoices)
    expenses = build_expenses(departments)

    inject_errors(students, invoices, payments, expenses)

    dirty_text_format(students, "dim_students", "Student_ID", "Full_Name")
    dirty_text_format(departments, "dim_departments", "Department_ID", "Manager_Name")
    dirty_text_format(expenses, "fact_expenses", "Expense_ID", "Vendor_Name")

    mixed_date_format(students, "dim_students", "Student_ID", ["Date_Of_Birth", "Enrollment_Date", "Dropout_Date"])
    mixed_date_format(departments, "dim_departments", "Department_ID", ["Created_Date"])
    mixed_date_format(invoices, "fact_tuition_invoices", "Invoice_ID", ["Invoice_Date", "Due_Date"])
    mixed_date_format(payments, "fact_payments", "Payment_ID", ["Payment_Date"])
    mixed_date_format(expenses, "fact_expenses", "Expense_ID", ["Expense_Date"])

    students = add_exact_duplicates(students, "dim_students", "Student_ID", DUPLICATES["dim_students"])
    invoices = add_exact_duplicates(invoices, "fact_tuition_invoices", "Invoice_ID", DUPLICATES["fact_tuition_invoices"])
    expenses = add_exact_duplicates(expenses, "fact_expenses", "Expense_ID", DUPLICATES["fact_expenses"])

    tables = {
        "dim_students": students, "dim_departments": departments,
        "fact_tuition_invoices": invoices, "fact_payments": payments, "fact_expenses": expenses,
    }
    for name, df in tables.items():
        df.to_csv(OUTPUT_DIR / f"{name}.csv", index=False, encoding="utf-8-sig")

    pd.DataFrame(manifest).to_csv(OUTPUT_DIR / "data_quality_manifest.csv", index=False, encoding="utf-8-sig")
    summary = validate_and_summarize(tables)
    (OUTPUT_DIR / "generation_summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
