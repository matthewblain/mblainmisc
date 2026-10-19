"""
=============================================================================
Script:       Givebutter Data Transformer & Exporter
Author:       Gemini, modified a lot by mblain, October 2026.
Description:  A tool to copy data from QBO to GB.
              Transforms sales and invoices CSVs from Quickbooks Online into
              Givebutter-compliant transaction payloads and soft credits.

              Can actually create the transactions using the Givebutter API.
              Soft Credits are not in the API, but require the tx ID and thus
              thus uses the API to create the TX and records that in the credit.

              The sales and transasctions and Customers are SELECT * From Table
              in the QBO API. TODO: Make it the actual JSON.
=============================================================================
"""

import argparse
import csv
import json
import os
import requests
import sys
import time
from dataclasses import dataclass, fields, field
from enum import Enum
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Static Mappings & Lookup Tables
# ---------------------------------------------------------------------------

GIVEBUTTER_API_URL = "https://api.givebutter.com/v1/transactions"
PRODUCT_SERVICE_MAP = {
    "Corporate Matching Gift": "CAMTBImpactFund",
    "Givebutter Fees": "INVALID",
    "The CAMTB Impact Fund": "CAMTBImpactFund",
    "The CAMTB Impact Fund - no tax receipt": "CAMTBImpactFund",
    "The Teen Ambassador Fund": "TeenAmbassador",
    "Unrestricted Donation": "Unrestricted",
    "Unrestricted donation - no tax receipt": "Unrestricted",
    "Unrestricted Grant": "Unrestricted",
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


class TransactionMethod(str, Enum):
    CARD = "card"
    ACH = "ach"
    CHECK = "check"
    CASH = "cash"
    VENMO = "venmo"
    PAYPAL = "paypal"
    OTHER = "other"


class TransactionStatus(str, Enum):
    SUCCEEDED = "succeeded"
    PENDING = "pending"
    FAILED = "failed"
    REFUNDED = "refunded"


@dataclass
class Address:
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class LineItem:
    type: str
    title: str
    amount: float
    quantity: int = 1
    description: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {k: v for k, v in self.__dict__.items() if v is not None}


@dataclass
class StoreTransactionRequest:
    """
    StoreTransactionRequest representation matching Givebutter v1 schema.
    """

    amount: float
    currency: str = "USD"
    campaign_id: Optional[str] = None
    campaign_code: Optional[str] = None
    contact_id: Optional[str] = None
    contact_external_id: Optional[str] = None
    external_id: Optional[str] = None
    external_label: Optional[str] = None

    # Status & Payment
    method: Optional[TransactionMethod] = None
    submethod: Optional[str] = None
    status: Optional[TransactionStatus] = None
    check_number: Optional[str] = None
    transacted_at: Optional[str] = None

    # Financial & Accounting
    fee: Optional[float] = None
    fee_covered: Optional[float] = None
    deductible_amount: Optional[float] = None
    fund_code: Optional[str] = None
    account_code: Optional[str] = None
    class_code: Optional[str] = None
    department_code: Optional[str] = None

    # Contact Details
    # Will create a new Contact with this info if no contact ID provided.
    # Not used in this script;
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    company: Optional[str] = None
    address_1: Optional[str] = None
    address_2: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    zip: Optional[str] = None
    country: Optional[str] = None

    # Notes & Dedication
    description: Optional[str] = None
    public_name: Optional[str] = None
    internal_note: Optional[str] = None
    thank_you_message: Optional[str] = None
    dedication_type: Optional[str] = None  # 'in_honor_of' or 'in_memory_of'
    dedication_name: Optional[str] = None
    dedication_recipient_name: Optional[str] = None

    # Line Items & Custom Fields
    line_items: List[LineItem] = field(default_factory=list)
    custom_fields: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Recursively converts dataclass instance into a clean dictionary."""
        data = {}
        for key, value in self.__dict__.items():
            if value is None:
                continue

            if isinstance(value, Enum):
                data[key] = value.value
            elif hasattr(value, "to_dict"):
                data[key] = value.to_dict()
            elif key == "line_items" and isinstance(value, list):
                if value:
                    data[key] = [
                        item.to_dict() if hasattr(item, "to_dict") else item
                        for item in value
                    ]
            elif key == "custom_fields" and isinstance(value, dict):
                if value:
                    data[key] = value
            else:
                data[key] = value

        return data


def process_sales_data(sales_csv: str, customer_csv: str, campaign_code: str):
    """
    Applies field mappings and product/service map lookup to generate outputs.
    """
    transactions = []
    soft_credits = []

    # Read Customer Data
    customers = {}
    with open(customer_csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            cust_id = row.get("Customer ID") or row.get("customer_id")
            if cust_id:
                customers[cust_id] = row

    # Read Sales Data and construct objects
    with open(sales_csv, mode="r", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for row in reader:
            soft_credit = None

            # 1. Product/Service -> Fund Code lookup
            product_service = row.get("Product service", "").strip()
            fund_code = PRODUCT_SERVICE_MAP.get(product_service, "")

            # Skip row if mapped as INVALID
            if fund_code == "INVALID":
                print(
                    f"[SKIP] Skipping transaction with Product/Service '{product_service}' (Marked INVALID): {row}"
                )
                continue

            # Extract Customer Info
            customer_id = row.get("Customer ID", "").strip()
            cust_info = customers.get(customer_id, {})

            # Calculate Amount ($)
            raw_amount = row.get("Line item amount")
            amount = float(raw_amount.replace("$", "").replace(",", "").strip())
            assert row.get("Currency") == "United States Dollar"

            method = TransactionMethod.OTHER  # TODO: Figure this out.

            # Construct Internal Note mapping
            tx_id = row.get("Transaction ID", "").strip()
            dept_name = row.get("Department name", "").strip()
            match row.get("Transaction type"):
                case "Sales Receipt":
                    internal_note = (
                        f"https://qbo.intuit.com/app/salesreceipt?txnId={tx_id}"
                    )
                case "Invoice":
                    internal_note = f"https://qbo.intuit.com/app/invoice?txnId={tx_id}"
                case _:
                    raise Exception(f"Unknown Transaction Type for {row}")

            internal_note = f"https://qbo.intuit.com/app/salesreceipt?txnId={tx_id}"
            if dept_name:
                internal_note += f"\nImpact Fund Grant: {dept_name}"
            if cust_info.get("ParentRef"):
                # There will be a soft credit here.
                internal_note += f"\nAttribution: {cust_info['Fully Qualified Name']}"

            # Check if this is a DAF type situation.
            # That is, there's a parent ID for the customer. The true
            # donor is the parent, the attribution goes to the leaf.
            if cust_info.get("ParentRef"):
                soft_credit = {}
                soft_credit["external_transaction_id"] = tx_id
                soft_credit["transaction_amount"] = amount
                soft_credit["contact_external_id"] = customer_id
                soft_credit["note"] = "DAF " + cust_info["Fully Qualified Name"]
                customer_id = cust_info.get("ParentRef")

            # Build StoreTransactionRequest payload
            tx_request = StoreTransactionRequest(
                campaign_code=campaign_code,
                amount=amount,
                method=method,
                fund_code=fund_code,
                transacted_at=row.get("Transaction date"),
                external_label="QBO-CATF",
                external_id=tx_id,
                internal_note=internal_note,
                contact_external_id=customer_id,
                currency="USD",
            )

            transactions.append(tx_request.to_dict())

            # Check for soft credit records if present
            soft_credit_contact = row.get("soft_credit_contact_id")
            if soft_credit:
                soft_credits.append(soft_credit)

    return transactions, soft_credits


def upload_transactions_to_givebutter(transactions: List[Dict[str, Any]], api_key: str):
    """Posts generated transactions directly to the Givebutter v1 API."""
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    success_count = 0
    failure_count = 0
    successes = []
    failures = []

    print(
        f"\nStarting API upload for {len(transactions)} transactions to Givebutter..."
    )

    for idx, tx in enumerate(transactions, start=1):
        try:
            response = requests.post(GIVEBUTTER_API_URL, json=tx, headers=headers)
            if response.status_code in (200, 201):
                success_count += 1
                transaction_resource = response.json()
                print(
                    f"[{idx} of {len(transactions)}] Successfully posted "
                    f"External ID: {tx.get('external_id')} "
                    f"Givebutter ID: {transaction_resource.get('number')}"
                )
                successes.append((tx, transaction_resource))
            else:
                failure_count += 1
                failure = f"[{idx} of {len(transactions)}] Failed External ID: {tx.get('external_id')} | Status: {response.status_code} | {response.text}"
                print(failure)
                failures.append((tx, failure))
        except requests.exceptions.RequestException as e:
            failure_count += 1
            failure = f"[{idx} of {len(transactions)}] Connection error: {e}"
            print(failure)
            failures.append((tx, failure))

        # Rate limit is 500tps so.... this could be vastly improved by
        # simply wiating for a 429 backoff response. Do max. 100tps for now.
        # https://docs.givebutter.com/api-reference/rate-limits
        time.sleep(0.01)

    print(f"\n--- Upload Finished ---")
    print(f"Successfully uploaded: {success_count}")
    print(f"Failed uploads: {failure_count}")

    return (successes, failures)


def add_txid_to_soft_credits(tx_uploads, soft_credits):
    """Add the transaction ID to soft credits.

    tx_results = list of (StoreTransactionRequest, TransactionResource)
    soft_credits = list of soft credits.

    Both are in dict/python form.
    """
    id_map = {}  # external id : givebutter id.

    for req, resp in tx_uploads:
        assert req["external_id"] not in id_map
        assert req["external_id"] == resp["external_id"]["external_id"]
        id_map[req["external_id"]] = resp["number"]

    for soft_credit in soft_credits:
        # This will fail if there were any failures uploading the transaction.
        # E.g. if there was a dupte of the external ID.
        gb_id = id_map.get(soft_credit["external_transaction_id"])
        if gb_id:
            soft_credit["transaction_id"] = gb_id
        else:
            print(
                f"WARNING: Could not find external transaction ID "
                f"{soft_credit["external_transaction_id"]} in list of created transactions."
            )

    return id_map


def write_output(data: List[Dict[str, Any]], file_path: str):
    """Saves output data as either JSON or CSV format."""
    if not data:
        print(f"[WARN] No data to write for {file_path}")
        return

    use_csv = os.path.splitext(file_path)[1] == ".csv"

    if use_csv:
        keys = list({key for item in data for key in item.keys()})
        with open(file_path, mode="w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=keys)
            writer.writeheader()
            writer.writerows(data)
    else:
        with open(file_path, mode="w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)


def main():
    parser = argparse.ArgumentParser(
        description="Process sales/customer CSVs and generate Givebutter transaction JSON outputs."
    )

    parser.add_argument(
        "--sales_csv",  #
        type=str,
        required=True,
        help="Path to the input Sales CSV file",
    )
    parser.add_argument(
        "--customer_csv",
        type=str,
        required=True,
        help="Path to the input Customer CSV file",
    )
    parser.add_argument(
        "--output_transaction_requests",
        type=str,
        required=False,
        help="Path to output generated transactions JSON file",
    )
    parser.add_argument(
        "--output_transactions",
        type=str,
        help="Path to output result transactions JSON file",
    )
    parser.add_argument(
        "--output_softcredits",
        type=str,
        required=True,
        help="Path to output generated soft credits JSON file",
    )
    parser.add_argument(
        "--campaign_code",
        type=str,
        required=True,
        help="campaign_code to use for transactions.",
    )
    parser.add_argument(
        "--api_key",
        type=str,
        required=False,
        help="Optional Givebutter API Secret Key to upload transactions automatically",
    )

    args = parser.parse_args()

    try:
        print(f"Processing '{args.sales_csv}' and '{args.customer_csv}'...")
        transactions, soft_credits = process_sales_data(
            args.sales_csv, args.customer_csv, args.campaign_code
        )
    except FileNotFoundError as e:
        print(f"[ERROR] Input file not found: {e}", file=sys.stderr)
        sys.exit(1)

    if args.output_transaction_requests:
        write_output(transactions, args.output_transaction_requests)
        print(
            f"[SUCCESS] Wrote {len(transactions)} transactions to '{args.output_transaction_requests}'"
        )

    # Output Soft Credits
    write_output(soft_credits, args.output_softcredits)
    print(
        f"[SUCCESS] Wrote {len(soft_credits)} soft credits to '{args.output_softcredits}'"
    )

    # Upload to Givebutter if API key is supplied
    if args.api_key:
        successes, failures = upload_transactions_to_givebutter(
            transactions, args.api_key
        )

        if args.output_transactions:
            # Successes is really both the req and the resp but that's OK
            # This is really for debugging purposes anyway.
            write_output(successes, args.output_transactions)

        # Update and re-write soft-credits

        add_txid_to_soft_credits(successes, soft_credits)
        write_output(soft_credits, args.output_softcredits)
        print(
            f"[SUCCESS] Re-Wrote {len(soft_credits)} soft credits to '{args.output_softcredits}'"
        )
        print("Now go to dashboard givebutter /settings/imports and upload that file.")


if __name__ == "__main__":
    main()
