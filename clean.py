import csv
import re
import sys
from datetime import datetime

VALID_STATUSES = {"Active", "Suspended", "Cancelled", "Refunded", "Flagged"}

def parse_amount(raw_val):
    if not raw_val or not raw_val.strip():
        raise ValueError("Empty amount")
    val_str = raw_val.strip().upper()
    is_usd = "USD" in val_str or "$" in val_str
    is_negative = False
    if val_str.startswith("(") and val_str.endswith(")"):
        is_negative = True
        val_str = val_str[1:-1]
    cleaned = re.sub(r"[^\d.-]", "", val_str)
    if not cleaned:
        raise ValueError(f"Invalid amount format: {raw_val}")
    amount = float(cleaned)
    if is_negative:
        amount = -abs(amount)
    if is_usd:
        amount *= 280.0
    return round(amount, 2)

def parse_date(date_str):
    if not date_str or not date_str.strip():
        raise ValueError("Empty date")
    date_str = date_str.strip()
    formats = ["%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d"]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            if 2000 <= dt.year <= 2050:
                return dt.date()
        except ValueError:
            continue
    raise ValueError(f"Unparseable date: {date_str}")

def clean_domain(domain_str):
    if not domain_str or not domain_str.strip():
        raise ValueError("Empty domain")
    d = domain_str.strip().lower()
    d = re.sub(r"^https?://", "", d)
    d = re.sub(r"^www\.", "", d)
    d = d.strip("/").rstrip(".")
    if "." not in d:
        raise ValueError(f"Invalid domain: {domain_str}")
    return d

def process_renewals(input_file, output_clean, output_issues):
    issues = []
    seen_records = set()
    rows_in = 0
    rows_kept = 0
    rows_dropped = 0
    rows_flagged = 0
    status_counts = {s: 0 for s in VALID_STATUSES}
    cleaned_data = []

    with open(input_file, mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows_in += 1
            rec_id = row.get("record_id", "").strip()
            
            # Skip empty rows completely
            if not rec_id:
                continue
                
            row_valid = True
            
            # Check for duplicate record_id
            if rec_id in seen_records:
                issues.append({
                    "record_id": rec_id,
                    "field": "record_id",
                    "raw_value": rec_id,
                    "problem": "Duplicate record_id",
                    "action_taken": "Dropped duplicate row"
                })
                rows_dropped += 1
                continue
            seen_records.add(rec_id)

            try:
                canonical_domain = clean_domain(row.get("domain", ""))
            except Exception as e:
                issues.append({
                    "record_id": rec_id,
                    "field": "domain",
                    "raw_value": row.get("domain"),
                    "problem": str(e),
                    "action_taken": "Flagged row"
                })
                canonical_domain = "unknown.pk"
                row_valid = False

            try:
                amount_pkr = parse_amount(row.get("amount_raw", ""))
            except Exception as e:
                issues.append({
                    "record_id": rec_id,
                    "field": "amount_raw",
                    "raw_value": row.get("amount_raw"),
                    "problem": str(e),
                    "action_taken": "Flagged row"
                })
                amount_pkr = 0.0
                row_valid = False

            try:
                reg_iso = parse_date(row.get("registered_on", "")).isoformat()
            except Exception:
                reg_iso = "2026-01-01"
                row_valid = False

            try:
                ren_iso = parse_date(row.get("renews_on", "")).isoformat()
            except Exception:
                ren_iso = "2026-08-15"
                row_valid = False

            try:
                billing_cycle = int(row.get("billing_cycle_months", 1))
            except ValueError:
                billing_cycle = 1

            status = row.get("status", "Active").strip()
            if status not in VALID_STATUSES:
                status = "Active"

            if not row_valid:
                status = "Flagged"
                rows_flagged += 1

            status_counts[status] += 1
            rows_kept += 1

            cleaned_data.append({
                "record_id": rec_id,
                "customer_id": row.get("customer_id", "").strip(),
                "canonical domain": canonical_domain,
                "service": row.get("service", "").strip(),
                "billing_cycle_months": billing_cycle,
                "amount_pkr": amount_pkr,
                "registered_on": reg_iso,
                "renews_on": ren_iso,
                "status": status,
                "contact_email": row.get("contact_email", "").strip()
            })

    with open(output_clean, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=[
            "record_id", "customer_id", "canonical domain", "service", 
            "billing_cycle_months", "amount_pkr", "registered_on", 
            "renews_on", "status", "contact_email"
        ])
        writer.writeheader()
        writer.writerows(cleaned_data)

    with open(output_issues, mode="w", encoding="utf-8", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=["record_id", "field", "raw_value", "problem", "action_taken"])
        writer.writeheader()
        writer.writerows(issues)

    print("=== SUMMARY ===")
    print(f"In: {rows_in} | Kept: {rows_kept} | Dropped: {rows_dropped} | Flagged: {rows_flagged}")
    print("Totals by Status:")
    for st, count in status_counts.items():
        print(f"  - {st}: {count}")

if __name__ == "__main__":
    process_renewals(sys.argv[1] if len(sys.argv) > 1 else "renewals_raw.csv", "clean.csv", "issues.csv")