"""
=============================================================================
Script:       Create Givebutter Teams and optionally Campaigns.
Author:       mblain
Description:  Takes a list of Campaigns and Teams and creates
              a team in the campaign for each one.
              Can create the campaign as well.

              This uses the internal Givebutter API, so it's not guarantteed
              to work if they change that.
              It requires using Givebutter in a browser than saving a
              HAR file of an API call and giving that to the tool.
=============================================================================
"""

import argparse
import csv
import json
import sys
import time
import urllib.parse
import requests


def get_public_api_session(api_key):
    """Return a requests session suitable for Givebutter API calls."""
    session = requests.Session()

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }

    session.headers.update(headers)
    return session


def create_internal_api_session(sample_internal_request):
    session = requests.Session()

    sample_internal_request
    entries = sample_internal_request.get("log", {}).get("entries", [])

    # Only look at the first entry.
    # We're going to take all the headers and let it replay them.
    har_headers = entries[0].get("request", {}).get("headers", [])
    request_cookies = entries[0].get("request", {}).get("cookies", [])

    request_headers = {}
    for header in har_headers:
        name = header.get("name")
        value = header.get("value")

        # Which headers to keep/discard?
        if name.lower() in ("host", "content-length", "connection"):
            continue

        request_headers[name] = value

    session.headers.update(request_headers)
    # session.cookies.update(request_cookies)

    return session


def get_campaigns(api_requests):
    """Get all active campaigns and return dict keyed by title."""
    url = f"https://api.givebutter.com/v1/campaigns/?per_page=99"

    print(f"[INFO] Getting existing campaigns", file=sys.stderr)
    response = api_requests.get(url)

    if response.status_code not in (200, 201):
        raise Exception(
            f"[ERROR] Failed to load campaigns | Status: {response.status_code} | {response.text}"
        )

    # Dictionary of campaigns by title.
    campaigns = {}

    campaigns_data = response.json()["data"]
    for campaign_data in campaigns_data:
        title = campaign_data["title"]
        id = campaign_data["id"]
        if title in campaigns:
            print(
                f"[WARNING] Campaign with title {title} already exists. Skipping {id} in favor of {campaigns[title]['id']} ",
                file=sys.stderr,
            )
            continue
        campaigns[title] = campaign_data

    # Todo: Pagination!
    assert not response.json()["links"]["next"]

    print(f"[INFO] Read {len(campaigns)} campaigns", file=sys.stderr)

    return campaigns


def get_campaign_members(campaign_id, api_requests):
    """Return the team members for a give campaign."""

    # Going for as many as we can get at once. Fewer API calls, but also
    # due to a pagination bug where the cursor doesn't seem to always be stable.
    url = f"https://api.givebutter.com/v1/campaigns/{campaign_id}/members?per_page=99"

    # Dictionary of members by display name.
    members = {}

    next_url = url
    page = 1
    while next_url:
        print(
            f"[INFO] Getting existing members for campaign {campaign_id} pg {page}.",
            file=sys.stderr,
        )
        response = api_requests.get(next_url)

        if response.status_code not in (200, 201):
            raise Exception(
                f"[ERROR] Failed to get team members for eam ID {campaign_id} | Status: {response.status_code} | {response.text}"
            )

        # print(response.text)

        response_json = response.json()
        members_data = response_json["data"]
        for member_data in members_data:
            title = member_data["display_name"]
            id = member_data["id"]
            if title in members:
                print(
                    f"[WARNING] member in {campaign_id} with display_name {title} already exists. Skipping {id} in favor of {members[title]['id']} ",
                    file=sys.stderr,
                )
                continue
            members[title] = member_data

        # Pagination: Run request until links.next is null.
        next_url = response_json["links"]["next"]
        page += 1

    # print(f"Found members for campaign {campaign_id}: {members}", file=sys.stderr)
    return members


def create_campaign(title, api_requests):
    """Sends a POST request to create a campaign."""
    url = "https://api.givebutter.com/v1/campaigns"

    payload = {
        "title": title,
        # "subtitle": "",
        "type": "fundraise",
        # "description": "",
        # "goal": 0,
        # "slug": "<string>",
        # "timezone": "<string>",
        "currency": "USD",
        "settings": [
            #    {"name": "hide_time_remaining", "value": true},
            {"name": "disable_team_fundraising", "value": False},
        ],
    }

    # print(f"Calling {url} with {payload}.")
    response = api_requests.post(url, json=payload)

    if response.status_code not in (200, 201):
        raise Exception(
            f"[ERROR] Failed create_campaign | Status: {response.status_code} | {response.text}"
        )

    created_campaign = response.json()
    # print(
    #    f"Created campaign {created_campaign['id']} with title {title}", file=sys.stderr
    # )

    return created_campaign


def create_team_member(campaign_id, display_name, internal_api_requests):
    """Sends a POST request to create a team member.

    Uses internal API. May or many not be stable across time.
    """

    url = f"https://givebutter.com/api/campaigns/{campaign_id}/members"

    payload = {
        "display_name": display_name,
        "goal": "",
        "team_id": "",
        "picture": "",
    }

    # print(f"Calling {url} with {payload}.", file=sys.stderr)
    response = internal_api_requests.post(url, json=payload)

    if response.status_code not in (200, 201):
        raise Exception(
            f"[ERROR] Failed create_team_member {campaign_id}, {display_name} | Status: {response.status_code} | {response.text}"
        )

    # print(f"Got response {url} with {response.text}.", file=sys.stderr)
    created_member = response.json()
    # print(
    #    f"Created member {created_member['id']} with display name {display_name}",
    #    file=sys.stderr,
    # )

    # Expected fields:
    # "id", "user_id", "contact_id", "short_display_name", "display_name",
    # "raw_display_name", "full_name", "first_name", "last_name", "email",
    # "phone", "picture", "raised", "raised_formatted", "raised_percentage",
    # "donors", "items", "goal", "goal_formatted", "description", "invites",
    # "slug", "url", "public", "created_at"

    return created_member


def create_campaigns(campaign_titles, api_requests):
    """Get or create campaign info."""

    campaigns = get_campaigns(api_requests)

    # print(f"Campaigns found: {campaigns}", file=sys.stderr)

    relevant_campaigns = {}

    for title in campaign_titles:
        if title in campaigns.keys():
            relevant_campaigns[title] = campaigns[title]
            print(
                f"[INFO] Campaign {title} already exists with id {relevant_campaigns[title]['id']}.",
                file=sys.stderr,
            )
        else:
            # Create a new one.
            relevant_campaigns[title] = create_campaign(title, api_requests)
            print(
                f"[INFO] Created new Campaign {title} with id {relevant_campaigns[title]['id']}.",
                file=sys.stderr,
            )

    # print(relevant_campaigns, file=sys.stderr)

    return relevant_campaigns


def create_campaigns_and_teammmembers(
    campaign_titles, team_member_names, api_requests, internal_api_requests
):

    campaigns = create_campaigns(campaign_titles, api_requests)
    campaign_id_map = dict([(k, v["id"]) for (k, v) in campaigns.items()])

    for campaign_title in campaign_titles:
        campaign_id = campaigns[campaign_title]["id"]
        campaign_members = get_campaign_members(campaign_id, api_requests)
        for name in team_member_names:
            if name in campaign_members:
                print(
                    f"[INFO] Member {name} in {campaign_id} already existed.",
                    file=sys.stderr,
                )
            else:
                print(
                    f"[INFO] Creating Member {name} in {campaign_id}.", file=sys.stderr
                )
                campaign_members[name] = create_team_member(
                    campaign_id, name, internal_api_requests
                )
        campaigns[campaign_title]["team_members"] = campaign_members

    return campaigns


def campaign_data_to_normal_form(campaigns):
    """Write a CSV file in a normalized form for the teams and campaigns.

    Headers: Campaign Title, Campaign ID, Team Member display name, team member ID.
    Basically the Campaign (title or name) and Team Member (display name) are
    the key into the other values.
    """

    results = []
    for campaign in campaigns.values():
        # Write the campaign itself w/o team info.
        # Useful both if there are no team members and for later matching
        # where some teams have team members and others do not.
        row = {
            "campaign_title": campaign["title"],
            "campaign_id": campaign["id"],
            "team_member_display_name": "",
            "team_member_id": "",
        }
        results.append(row)

        team_members = campaign.get("team_members", {})
        for team_member in team_members.values():
            row = {
                "campaign_title": campaign["title"],
                "campaign_id": campaign["id"],
                "team_member_display_name": team_member["display_name"],
                "team_member_id": team_member["id"],
            }
            results.append(row)

    return results


def main():
    parser = argparse.ArgumentParser(
        description="Batch create Givebutter teams and members."
    )
    parser.add_argument(
        "-k", "--api-key", required=True, help="Givebutter API Secret Key"
    )
    parser.add_argument(
        "-x",
        "--request-har",
        help="Saved HAR of an internal API call seen in a browser",
    )
    parser.add_argument(
        "--campaign-list",
        required=True,
        dest="campaign_list",
        help="Path to the file containing a list of campaigns",
    )
    parser.add_argument(
        "--team-member-list",
        dest="team_member_list",
        help="Path to the file containing a list of team_members to create for each campaign",
    )
    parser.add_argument(
        "-o",
        "--output-csv",
        required=True,
        dest="output_csv",
        help="Path to the output CSV file listing the matrix of campaigns and teams",
    )
    parser.add_argument(
        "--output-json",
        help="Path to the output JSON file with all the returned data.",
    )

    args = parser.parse_args()
    if args.team_member_list and not args.request_har:
        parser.error("--request-har is required when --team-member-list is specified.")

    with open(args.campaign_list, mode="r", encoding="utf-8-sig") as file:
        campaign_titles = file.readlines()
        campaign_titles = [l.strip() for l in campaign_titles]

    if args.team_member_list:
        with open(args.team_member_list, mode="r", encoding="utf-8-sig") as file:
            team_members = file.readlines()
            team_members = [l.strip() for l in team_members]
    else:
        team_members = []

    with open(args.request_har, "r", encoding="utf-8") as file:
        sample_internal_request = json.load(file)

    api_requests = get_public_api_session(args.api_key)
    internal_api_requests = create_internal_api_session(sample_internal_request)

    results = create_campaigns_and_teammmembers(
        campaign_titles, team_members, api_requests, internal_api_requests
    )
    # This is a dict of campaign and team info...

    if args.output_json:
        with open(args.output_json, mode="w", encoding="utf-8") as f:
            json.dump(results, f, indent=2)

    normalized_results = campaign_data_to_normal_form(results)

    with open(args.output_csv, mode="w", encoding="utf-8", newline="") as f:
        field_names = [
            "campaign_title",
            "campaign_id",
            "team_member_display_name",
            "team_member_id",
        ]
        writer = csv.DictWriter(f, fieldnames=normalized_results[0].keys())
        writer.writeheader()
        writer.writerows(normalized_results)

    print(f"Wrote {len(normalized_results)} records.", file=sys.stderr)


if __name__ == "__main__":
    main()
