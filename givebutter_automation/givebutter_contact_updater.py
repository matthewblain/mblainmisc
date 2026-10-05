"""
=============================================================================
Script:       Batch Update Contacts (Givebutter API)
Author:       Gemini, then modified a lot by mblain
Description:  Reads a CSV file containing Givebutter Contact IDs and updated
              fields, then issues PUT requests to update each contact via
              the Givebutter v2 API.
=============================================================================
"""

import argparse
import csv
import json
import time
import requests

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BASE_URL = "https://api.givebutter.com/v1/contacts"


# Supported to send to Givebutter
# From https://docs.givebutter.com/api-reference/contacts/update-a-contact

__givebutter__contact__api__options__ = """{
  "id": "<string>",
  "external_id": "<string>",
  "contact_since": "<string>",
  "type": "<string>",
  "prefix": "<string>",
  "first_name": "<string>",
  "preferred_name": "<string>",
  "middle_name": "<string>",
  "last_name": "<string>",
  "suffix": "<string>",
  "gender": "<string>",
  "pronouns": "<string>",
  "dob": "<string>",
  "company": "<string>",
  "employer": "<string>",
  "company_name": "<string>",
  "title": "<string>",
  "website_url": "<string>",
  "twitter_url": "<string>",
  "linkedin_url": "<string>",
  "facebook_url": "<string>",
  "tiktok_url": "<string>",
  "instagram_url": "<string>",
  "emails": [
    {
      "type": "<string>",
      "value": "<string>"
    }
  ],
  "phones": [
    {
      "type": "<string>",
      "value": "<string>"
    }
  ],
  "primary_email": "<string>",
  "primary_phone": "<string>",
  "note": "<string>",
  "addresses": [
    {
      "address_1": "<string>",
      "address_2": "<string>",
      "city": "<string>",
      "state": "<string>",
      "zipcode": "<string>",
      "country": "<string>",
      "type": "<string>",
      "is_primary": true,
      "created_at": "2023-11-07T05:31:56Z",
      "updated_at": "2023-11-07T05:31:56Z"
    }
  ],
  "primary_address": {
    "address_1": "<string>",
    "address_2": "<string>",
    "city": "<string>",
    "state": "<string>",
    "zipcode": "<string>",
    "country": "<string>",
    "type": "<string>",
    "is_primary": true,
    "created_at": "2023-11-07T05:31:56Z",
    "updated_at": "2023-11-07T05:31:56Z"
  },
  "last_donation_amount": "<string>",
  "stats": {
    "total_contributions": "<string>",
    "recurring_contributions": "<string>"
  },
  "tags": "<string>",
  "custom_fields": [
    "<unknown>"
  ],
  "external_ids": [
    {
      "id": 123,
      "label": "<string>",
      "external_id": "<string>",
      "created_at": "<string>",
      "updated_at": "<string>"
    }
  ],
  "is_email_subscribed": "<string>",
  "is_phone_subscribed": "<string>",
  "is_address_subscribed": "<string>",
  "email_opt_in": "<string>",
  "sms_opt_in": "<string>",
  "address_unsubscribed_at": "<string>",
  "archived_at": "<string>",
  "created_at": "<string>",
  "updated_at": "<string>",
  "salutation_name": "<string>",
  "point_of_contact": {
    "id": "<string>",
    "type": "<string>",
    "prefix": "<string>",
    "first_name": "<string>",
    "middle_name": "<string>",
    "last_name": "<string>",
    "suffix": "<string>",
    "gender": "<string>",
    "pronouns": "<string>",
    "dob": "<string>",
    "employer": "<string>",
    "title": "<string>",
    "twitter_url": "<string>",
    "linkedin_url": "<string>",
    "facebook_url": "<string>",
    "tiktok_url": "<string>",
    "instagram_url": "<string>",
    "website_url": "<string>",
    "emails": {},
    "phones": {},
    "primary_email": "<string>",
    "primary_phone": "<string>",
    "is_email_subscribed": "<string>",
    "is_phone_subscribed": "<string>",
    "is_address_subscribed": "<string>",
    "address_unsubscribed_at": "<string>",
    "archived_at": "<string>",
    "created_at": "<string>",
    "updated_at": "<string>",
    "first_time_supporter_at": "<string>"
  },
  "associated_companies": [
    {
      "id": "<string>",
      "type": "<string>",
      "company_name": "<string>",
      "name_display": "<string>",
      "title": "<string>",
      "twitter_url": "<string>",
      "linkedin_url": "<string>",
      "facebook_url": "<string>",
      "tiktok_url": "<string>",
      "instagram_url": "<string>",
      "website_url": "<string>",
      "image_url": "<string>",
      "emails": {},
      "phones": {},
      "primary_email": "<string>",
      "primary_phone": "<string>",
      "is_email_subscribed": "<string>",
      "is_phone_subscribed": "<string>",
      "is_address_subscribed": "<string>",
      "address_unsubscribed_at": "<string>",
      "note": "<string>",
      "addresses": [
        {
          "id": 123,
          "account_id": 123,
          "name": "<string>",
          "address_1": "<string>",
          "address_2": "<string>",
          "city": "<string>",
          "state": "<string>",
          "zipcode": "<string>",
          "country": "<string>",
          "type": "<string>",
          "is_primary": true,
          "created_at": "2023-11-07T05:31:56Z",
          "updated_at": "2023-11-07T05:31:56Z"
        }
      ],
      "primary_address": {
        "id": 123,
        "account_id": 123,
        "name": "<string>",
        "address_1": "<string>",
        "address_2": "<string>",
        "city": "<string>",
        "state": "<string>",
        "zipcode": "<string>",
        "country": "<string>",
        "type": "<string>",
        "is_primary": true,
        "created_at": "2023-11-07T05:31:56Z",
        "updated_at": "2023-11-07T05:31:56Z"
      },
      "archived_at": "<string>",
      "created_at": "<string>",
      "updated_at": "<string>",
      "first_time_supporter_at": "<string>"
    }
  ]
}
"""


def get_valid_fields():
    """Get the list of valid fields from the API description.

    Yes this is absurd to do dynamically.
    But this is not a frequetnly run script so it can be optimized later.

    TODO: Figure out what to do with subfields (e.g. primary_address)
    or multiple value fields (e.g. addresses)

    TODO: Parse the API from https://givebutter.com/docs/api.json instead.
    """
    valid_fields = []
    api_fields = json.loads(__givebutter__contact__api__options__)

    for k, v in api_fields.items():
        if v == "<string>" and k != "id":
            valid_fields.append(k)

    return valid_fields


VALID_FIELDS = get_valid_fields()


def update_contact(contact_id, payload, headers):
    """Sends a PUT request to update a single contact by ID."""
    url = f"{BASE_URL}/{contact_id}"
    try:
        print(f"Calling {url} with {payload}.")
        response = requests.put(url, json=payload, headers=headers)

        if response.status_code in (200, 201):
            print(f"[SUCCESS] Updated contact ID: {contact_id}")
            return True
        else:
            print(
                f"[ERROR] Failed contact ID {contact_id} | Status: {response.status_code} | {response.text}"
            )
            return False

    except requests.exceptions.RequestException as e:
        print(f"[EXCEPT] Connection error for contact ID {contact_id}: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(
        description="Batch update Givebutter contacts from a CSV file."
    )
    parser.add_argument(
        "-k", "--api-key", required=True, help="Givebutter API Secret Key"
    )
    parser.add_argument(
        "-c",
        "--csv",
        required=True,
        dest="csv_file_path",
        help="Path to the CSV file containing contact updates",
    )

    args = parser.parse_args()

    with open(args.csv_file_path, mode="r", encoding="utf-8-sig") as file:
        reader = csv.DictReader(file)

        if "id" not in reader.fieldnames:
            raise ValueError(
                "CSV file must contain an 'id' column with Givebutter Contact IDs."
            )

        success_count = 0
        failure_count = 0

        print(f"Starting batch PUT update from {args.csv_file_path}...\n")

        headers = {
            "Authorization": f"Bearer {args.api_key}",
            "Accept": "application/json",
            "Content-Type": "application/json",
        }

        for row in reader:
            contact_id = row.get("id", "").strip()
            if not contact_id:
                print(
                    f"[SKIP] Skipping row with missing contact ID at row {reader.line_num}"
                )
                continue

            # TODO: Check if first_name,last_name are set because the API will
            # reject it if not. 

            # Build payload with non-empty fields matching VALID_FIELDS
            payload = {}
            for field in VALID_FIELDS:
                if field in row and row[field].strip() != "":
                    payload[field] = row[field].strip()

            if not payload:
                print(
                    f"[SKIP] No valid update fields found for contact ID {contact_id} at row {reader.line_num}"
                )
                continue

            # Execute update using PUT
            if update_contact(contact_id, payload, headers):
                success_count += 1
            else:
                failure_count += 1

            # Pause briefly to handle rate limits gracefully
            # TODO: Rate limit to much faster!
            # API limit is normally 500RPS and it'll report a 429 if exceeded.
            time.sleep(0.1)

        print(f"\n--- Batch Process Finished ---")
        print(f"Successfully updated: {success_count}")
        print(f"Failed: {failure_count}")


if __name__ == "__main__":
    main()
