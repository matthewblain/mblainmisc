"""
Benevity Donation Report Transformer

This script converts multi-block Benevity donation reports into a flat
CSV format suitable for import into QuickBooks Online as invoices.

This is V2 because as of September 2026 the CSV file is now pure data
it doesn't have a header, it has way more data.


THe original  was written almost entirely with Google Gemini, then re-organized a bit
and some bugs fixed.... -mblain 20apr2026
Lots of changes --mblain 02oct2026

Transformation Logic:
* Splits each donation row into two separate entries:
    - An individual donation row ('The CAMTB Impact Fund')
    - A corporate matching gift row ('Corporate Matching Gift')
*. Reformats all dates to M/D/YYYY and generates unique Invoice Numbers
   using the Disbursement ID.

Usage:
    python script.py <input_report.csv> <output_invoices.csv>
"""

import csv
import sys
from datetime import datetime




def format_period_ending_date(date_str):
    parts = date_str.split()
    dt = datetime.strptime(f"{parts[1]} {parts[2]} {parts[3]}", "%d %b %Y")
    return f"{dt.month}/{dt.day}/{dt.year}"

def format_donation_date(date_str):
    dt = datetime.fromisoformat(date_str)
    return f"{dt.month}/{dt.day}/{dt.year}"



def process_input_rows(reader):
    """Parses raw CSV rows to extract donation and matching gift data.
    """
    disbursement_id = "UNKNOWN"
    due_date = ""
    output_rows = []

    for row in reader:
        company = row["Company Name"]
        inv_date = format_donation_date(row["Donation Date"])
        donor = f"{row['Donor First Name']} {row['Donor Last Name']}"
        tx_id = row["Transaction ID"]
        comment = f"{row['Donation Method']} {row['Donation Frequency']} {row['Disbursement From (Grantor)']}"
 
        frequency = row["Donation Frequency"]
        user_amt = row["Donation Amount"]
        match_amt = row["Match Amount"]
        # Todo: Consider "Cause Support Fee" and "Merchant Fee"
        due_date = format_donation_date(row["Disbursement Date"])


        # Row 1: Individual Donation
        output_rows.append(
            {
                "*InvoiceNo": f"Benevity-{tx_id}",
                "*Customer": f"Benevity: {donor}",
                "*InvoiceDate": inv_date,
                "*DueDate": due_date,
                "Item(Product/Service)": "The CAMTB Impact Fund - no tax receipt",
                "ItemDescription": f"Benevity - {tx_id} - {frequency} - {comment}",
                "*ItemAmount": user_amt,
            }
        )

        # Row 2: Corporate Match
        try:
            if float(match_amt) > 0:
                output_rows.append(
                    {
                        "*InvoiceNo": f"Benevity-{tx_id}-M",
                        "*Customer": f"Benevity: {row['Company Name']}",
                        "*InvoiceDate": inv_date,
                        "*DueDate": due_date,
                        "Item(Product/Service)": "Corporate Matching Gift",
                        "ItemDescription": f"Benevity - {tx_id} - Matching {donor}",
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
        reader = csv.DictReader(infile)
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
