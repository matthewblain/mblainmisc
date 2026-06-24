"""
Quickbooks Reports to EveryAction Report Transformer

This script converts the Sales by Customer report from QBO
into a CSV suitable for import as donation info into EveryAction.

Input:
 Sales by Customer CSV
 Customer to VANID list  CSV
Output:
 Report suitable for import using EveryAction… Bulk Upload.


The input CSVs are "reports" so require a bit of finding the raw data.

The output has the following columnts:
VANID, Person, Date, Amount, Note, Designation, Payment Method, Status,
 Contact Attribution, Attribution Type, Attribution Amount

-mblain 21apr2026

Usage:
  script <sales_by_customer.csv> <customer_vanid.csv> <out_contribution_info.csv>
"""

import csv
import sys
from datetime import datetime


def get_data_header(reader):
    """Walk through a CSV file to find the headers of the data section.

    The format of QBO CSV Reports is something like
    Report Title,,,
    Org Name,,,
    Timeframe,,,
    <blank line>
    Column,Head,Ers
    Data,And,Stuff
    More,Data,Etc
    <blank lines>
    Timestamp,,,,

    Thjs function will discard the first part, get the next row,
    the headers, and return that.

    It iterator will then be good going forward.
    """
    header_is_next = False
    for row in reader:
        if header_is_next:
            return row
        if not row:
            header_is_next = True


def find_matchee(item_description):
    """Find the 'customer' this match is for.

    We're assuming this is in the description, which will look like:
     Blah - BlahID - Matching {matchee}.
    """
    i = item_description.find("Matching")
    if i < 0:
        return None
    m = item_description[i + 9 :]  # Skips space or maybe ":".
    return m.strip()


class CustomerInfo:
    """Info about a 'customer'.

    Stored w/ a key of 'customer name', which is always a single level.
    So the customer_type is used by the 'child' but looked up by 'parent'.

    vanid = vanid of the actial donor
    attribution_vanid = donor to attribte
    customer_type = customertype from QBO.
    attribution_type = EA attribution type.
    """

    def __init__(
        self, vanid, attribution_vanid=None, customer_type=None, attribution_type=None
    ):
        self.vanid = vanid
        self.attribution_vanid = attribution_vanid
        self.customer_type = customer_type
        self.attribution_type = attribution_type


def map_customerid_to_info(customer_reader):
    """Map the customer to CustomerInfo.

    Expected headers in CSV reader: Customer full name,VANID

    Note: the customer key is configureable in the QBO options.
    """
    customer_to_vanid = {}
    headers = get_data_header(customer_reader)

    customer_key = None
    for k in [
        "Client full name",
        "Customer full name",
        "Donor full name",
        "Guest full name",
        "Member full name",
        "Patient full name",
        "Tenant full name",
    ]:
        if k in headers:
            customer_key = k
            break
    if not customer_key:
        raise Exception("Customer key not found.")

    # The "Customer Type" describes various non-individual
    # entities. Some valid types for attribution on the EA side:
    #  Attribution
    #  Board Member Giving
    #  Corporate Matching
    #  Donor Match
    #  Donor-Advised Fund
    #  Family / Private Foundation
    #  Gift Membership
    #  Peer-to-Peer
    #  Tribute Gift
    #  Workplace Giving
    attribution_types = {
        "DAF": "Donor-Advised Fund",
    }

    for row in customer_reader:
        if not row:
            # The end of the file has a few blank lines then a footer. Stop.
            break
        customer = dict(zip(headers, row))
        vanid = customer["VANID"]
        if vanid:
            name = customer[customer_key]
            if ":" in name:
                parent_customer_name, customer_name = name.split(":")
                # Input rows should be sorted so we see the parent first. E.g.:
                # Example Foundation,123214
                # Example Foundation:Big Donor (EF),213432
                # Parent is donating entity; sub-customer who to attribute.
                parent_info = customer_to_vanid[parent_customer_name]
                print("%s %s %s" % (parent_customer_name, customer_name, customer))
                attribution_type = attribution_types[parent_info.customer_type]
                customer_to_vanid[customer_name] = CustomerInfo(
                    parent_info.vanid,
                    vanid,
                    customer["Customer type"],
                    attribution_type,
                )
            else:
                customer_to_vanid[name] = CustomerInfo(
                    vanid, None, customer["Customer type"]
                )
    return customer_to_vanid


def process_input_rows(sales_reader, customers_info):
    """Parses raw CSV rows and transforms them.

    So much bizlogic embedded here....

    """
    output_rows = []
    issues = []

    headers = get_data_header(sales_reader)
    # Expected headers:
    # Customer,Transaction date,Product/Service full name,Description,Amount
    customer_key = None
    # QBO is configureable to use different Customer labels.
    for k in [
        "Client",
        "Customer",
        "Donor",
        "Guest",
        "Member",
        "Patient",
        "Tenant",
    ]:
        if k in headers:
            customer_key = k
            break
    if not customer_key:
        raise Exception("Customer key not found.")

    # Go through the list of sales.
    # Figure out the amount, the designation, possibly the attribution.
    # Designation is hard-coded for now.
    # Attribution has two styles: Newer sub-customer style, and older
    # description-in-corporate-match style.

    for row in sales_reader:
        if not row:
            # Shouln't get here due to TOTAL row, but if so, stop now.
            break

        if row[0] == "TOTAL" and row[1] == "":
            # Reports have a TOTAL summary row which we will consider the end.
            break

        sale = dict(zip(headers, row))

        customer = sale[customer_key]

        contact_attribution = ""
        attribution_type = ""
        attribution_amount = ""

        if customer in customers_info:
            customer_info = customers_info[customer]
            if customer_info.attribution_type:
                attribution_type = customer_info.attribution_type
                attribution_amount = sale["Amount"]
                contact_attribution = customer_info.attribution_vanid
        else:
            issues.append(f"No vanid for customer: {row}")
            continue

        note = sale["Description"].strip()
        if "Your donation is fully tax deductible" in note:
            note = ""

        # Handle different designations.
        item = sale["Product/Service full name"]

        match item:
            case "The CAMTB Impact Fund" | "The CAMTB Impact Fund - no tax receipt":
                designation = "Trails Foundation CAMTB Action Fund"

            case "The Teen Ambassador Fund":
                # For now we're going to skip reporting Teen Ambassador donations.
                # TODO: Create designation in EA and add that here.
                issues.append(f"No EA designation: {row}")
                continue

            case (
                "Unrestricted Donation"
                | "Unrestricted donation - no tax receipt"
                | "Unrestricted Grant"
                | "Other CATF projects"
            ):
                # For now we're going to skip reporting CATF direct donations.
                # TODO: Create designation in EA and add that here.
                issues.append(f"No EA designation: {row}")
                continue

            case "Corporate Matching Gift":
                # For now we're going to allocate all of these to the CAMTB Impact Fund.
                # This may change in the future.
                designation = "Trails Foundation CAMTB Action Fund"
                attribution_type = "Corporate Matching"
                attribution_amount = sale["Amount"]

                # Prefer old attribution style. Todo: Delete old style?
                matchee = find_matchee(sale["Description"])
                if not matchee:
                    if contact_attribution:
                        # We are using new-style sub-customer attribution.
                        continue
                    issues.append(f"No matchee found: {row}")
                    continue
                if matchee not in customer_to_vanid:
                    issues.append(f"No vanid for matchee: {row}")
                    continue
                contact_attribution = customer_to_vanid[matchee].vanid

            case _:
                raise Exception(f"Unknown Product/Service: {item} for {row}")

        # Row 1: Individual Donation
        output_rows.append(
            {
                "VANID": customer_info.vanid,
                "Person": customer,
                "Date": sale["Transaction date"],
                "Amount": sale["Amount"],
                "Note": note,
                "Designation": designation,
                "Payment Method": "Unknown",
                "Status": "Settled",
                "Contact Attribution": contact_attribution,
                "Attribution Type": attribution_type,
                "Attribution Amount": attribution_amount,
            }
        )

    return output_rows, issues


def process_reports(
    sales_by_customer_filename, customer_vanid_filename, output_filename
):
    """Coordinates the reading, processing, and writing of the donation report.

    Args:
        sales_by_customer_filename (str): Path to the Sales by Customer details CSV file.
        customer_vanid_filename: Path to the customer->VanID CSV.
        output_file (str): Path where the transformed CSV should be saved.
    """
    with open(
        sales_by_customer_filename, mode="r", encoding="utf-8"
    ) as sales_by_customer_file:
        with open(
            customer_vanid_filename, mode="r", encoding="utf-8"
        ) as customer_vanid_file:
            sales_reader = csv.reader(sales_by_customer_file)
            customer_reader = csv.reader(customer_vanid_file)
            customer_to_info = map_customerid_to_info(customer_reader)
            output_rows, issues = process_input_rows(sales_reader, customer_to_info)

    # Write Output
    headers = [
        "VANID",
        "Person",
        "Date",
        "Amount",
        "Note",
        "Designation",
        "Payment Method",
        "Status",
        "Contact Attribution",
        "Attribution Type",
        "Attribution Amount",
    ]

    with open(output_filename, mode="w", newline="", encoding="utf-8") as outfile:
        writer = csv.DictWriter(outfile, fieldnames=headers)
        writer.writeheader()
        writer.writerows(output_rows)

    return len(output_rows), issues


def main():
    # Check if input and output filenames were provided
    if len(sys.argv) != 4:
        print(
            "Usage: script <sales_by_customer.csv> <customer_vanid.csv> <out_contribution_info.csv>",
            file=sys.stderr,
        )
        sys.exit(1)

    sales_by_customer_filename = sys.argv[1]
    customer_vanid_filename = sys.argv[2]
    output_filename = sys.argv[3]

    row_count, issues = process_reports(
        sales_by_customer_filename, customer_vanid_filename, output_filename
    )

    print(f"Found {len(issues)} issues:")
    print("\n".join(issues))

    print(f"Created '{output_filename}' with {row_count} rows.")


if __name__ == "__main__":
    main()
