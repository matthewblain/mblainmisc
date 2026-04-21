"""
Benevity Donation Report Transformer

This script converts multi-block Benevity donation reports into a flat
CSV format suitable for import into QuickBooks Online as invoices.

It was written almost entirely with Google Gemini, then re-organized a bit
and some bugs fixed.... -mblain 20apr2026

Transformation Logic:
1. Extracts metadata (Disbursement ID, Period Ending) from the report header.
2. Identifies the main donation table starting with the 'Company' header.
3. Splits each donation row into two separate entries:
    - An individual donation row ('The CAMTB Impact Fund')
    - A corporate matching gift row ('Corporate Matching Gift')
4. Reformats all dates to M/D/YYYY and generates unique Invoice Numbers
   using the Disbursement ID.

Usage:
    python script.py <input_report.csv> <output_invoices.csv>
"""

import csv
import sys
from datetime import datetime


def format_date(date_str):
    """Converts varying Benevity date formats into a standard M/D/YYYY format.

    Args:
        date_str (str): The date string to convert. Can be ISO format
            (2026-02-03T...) or header format (Mon 16 Mar 2026...).

    Returns:
        str: The formatted date string (e.g., '3/16/2026').
             Returns original string if parsing fails.
    """
    try:
        if "T" in date_str:
            dt = datetime.strptime(date_str.split("T")[0], "%Y-%m-%d")
        else:
            parts = date_str.split()
            dt = datetime.strptime(f"{parts[1]} {parts[2]} {parts[3]}", "%d %b %Y")
        return f"{dt.month}/{dt.day}/{dt.year}"
    except Exception:
        return date_str


def process_input_rows(reader):
    """Parses raw CSV rows to extract donation and matching gift data.

    Initializes with a standard reader to capture metadata, then switches to
    DictReader for the main data block to improve readability and maintainability.
    """
    disbursement_id = "UNKNOWN"
    due_date = ""
    output_rows = []

    # Stage 1: Use the standard reader for metadata and finding the header
    for row in reader:
        if not row:
            continue

        if row[0] == "Disbursement ID":
            disbursement_id = row[1]
        elif row[0] == "Period Ending":
            due_date = format_date(row[1])
        elif row[0] == "Company" and row[1] == "Project":
            # We found the header!
            # row is currently ['Company', 'Project', 'Donation Date', ...]
            headers = row
            break

    # We're now in dictionary mode....
    for row_as_list in reader:
        row = dict(zip(headers, row_as_list))
        # Totals row will have a blank 'project'.
        if row["Company"] == "Totals" and row["Project"] == "":
            break

        company = row["Company"]
        inv_date = format_date(row["Donation Date"])
        donor = f"{row['Donor First Name']} {row['Donor Last Name']}"
        tx_id = row["Transaction ID"]
        comment = row["Comment"]
        frequency = row["Donation Frequency"]
        user_amt = row["Total Donation to be Acknowledged"]
        match_amt = row["Match Amount"]
        # Todo: Consider "Cause Support Fee" and "Merchant Fee"

        # Row 1: Individual Donation
        output_rows.append(
            {
                "*InvoiceNo": f"Benevity-{tx_id}",
                "*Customer": donor,
                "*InvoiceDate": inv_date,
                "*DueDate": due_date,
                "Item(Product/Service)": "The CAMTB Impact Fund",
                "ItemDescription": f"Benevity - {frequency} - {comment}",
                "*ItemAmount": user_amt,
            }
        )

        # Row 2: Corporate Match
        try:
            if float(match_amt) > 0:
                output_rows.append(
                    {
                        "*InvoiceNo": f"Benevity-{tx_id}-M",
                        "*Customer": company,
                        "*InvoiceDate": inv_date,
                        "*DueDate": due_date,
                        "Item(Product/Service)": "Corporate Matching Gift",
                        "ItemDescription": f"Benevity - Match - {tx_id}",
                        "*ItemAmount": match_amt,
                    }
                )
        except (ValueError, TypeError):
            pass

    return output_rows


def process_benevity_report(input_file, output_file):
    """Coordinates the reading, processing, and writing of the donation report.

    Args:
        input_file (str): Path to the raw Benevity CSV file.
        output_file (str): Path where the transformed CSV should be saved.
    """
    with open(input_file, mode="r", encoding="utf-8") as infile:
        reader = csv.reader(infile)
        output_rows = process_input_rows(reader)

    # Write Output
    headers = [
        "*InvoiceNo",
        "*Customer",
        "*InvoiceDate",
        "*DueDate",
        "Terms",
        "Location",
        "Memo",
        "Item(Product/Service)",
        "ItemDescription",
        "ItemQuantity",
        "ItemRate",
        "*ItemAmount",
        "Service Date",
    ]

    with open(output_file, mode="w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(output_rows)

    return len(output_rows)


def main():
    # Check if input and output filenames were provided
    if len(sys.argv) != 3:
        print("Usage: script.py <input_csv> <output_csv>", file=sys.stderr)
        sys.exit(1)

    input_filename = sys.argv[1]
    output_filename = sys.argv[2]

    row_count = process_benevity_report(input_filename, output_filename)

    print(f"Success! Created '{output_filename}' with {row_count} rows.")


if __name__ == "__main__":
    main()
