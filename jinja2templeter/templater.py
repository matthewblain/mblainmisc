# Jinja2 CSV template tool.
#
# This is a really simple tool: It loads a jinja2 template
# and a CSV file and renders the tempalte.
#
# mblain 27sep2024

# Generate content using a jinja2 template and a CSV file.
# Also supports uploading it to Wordpress.
#
# Usage:
#  templater -t template_filename -i csv_data -o output_filename
#    [-w Wordpress endpoint] [-k sort_key1] [-k sort_key2]
#
# The wordpress enpoint should be the WP-JSON endpoint for the post or page.
# E.g.
#    "https://blog.example.com/wp-json/wp/v2/pages/2345"
# or "https://blog.example.com/wp-json/wp/v2/posts/1234"
#
# The Wordpress Application credentials must be in the
# env vars TEMPLATER_WP_USER and TEMPLATER_WP_ASP.
#
# rclone is one tool to get CSV files out of google docs.
# rclone.exe copyto "remotename:path/to/sheet.csv"
#  "questionnaire-info.csv" --drive-export-formats csv


import argparse
import base64
import csv
import os
import re
import requests
import sys
import datetime
import jinja2

# Run the template...


def update_wp_page(wordpress_url, wordpress_username, wordpress_asp, content):
    """Simple uploader to replace the content of a Wordpress page or post."""

    # Encode credentials for Basic Authentication
    credentials = f"{wordpress_username}:{wordpress_asp}"
    token = base64.b64encode(credentials.encode()).decode("utf-8")

    headers = {"Authorization": f"Basic {token}", "Content-Type": "application/json"}

    upload_info = {"content": content}
    response = requests.post(wordpress_url, headers=headers, json=upload_info)

    if response.status_code == 200:
        # Not quite sure what if anything to respond with here!
        return response.json()
    else:
        raise Exception(
            f"Failed to create page. Status code: {response.status_code} Message: {response.text}"
        )


def render_template(template_filename, csv_data):

    template_dir = os.path.dirname(template_filename) or "."
    template_basename = os.path.basename(template_filename)

    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(template_dir),
        autoescape=jinja2.select_autoescape(),
        lstrip_blocks=True,
    )
    try:
        template = env.get_template(template_basename)
    except jinja2.exceptions.TemplateSyntaxError as e:
        print("%s[%d]: %s" % (e.filename, e.lineno, e.message), file=sys.stderr)
        # raise e
        return

    # {{ row['']  }}
    lastupdated = datetime.datetime.now().strftime("%m/%d/%y %H:%M")
    return template.render(csv_data=csv_data, lastupdated=lastupdated)


def sort_csv_data(reader, sort_keys):
    # Data will always be materalized into a list.
    data = list(reader)
    if sort_keys:
        for key in sort_keys:
            data.sort(key=lambda r: r.get(key))
    return data


def join_data(data, jreader, join_lkey, join_rkey, join_value):
    # Join data with data in jreader
    # Modifies data in-place.
    # Todo: Allow a different join key on the left and right.

    join_dict = {}

    for row in jreader:
        join_dict.setdefault(row[join_rkey], []).append(row[join_value])

    for row in data:
        row[join_value] = join_dict.get(row[join_lkey])


# Usage:
def main():
    parser = argparse.ArgumentParser(
        description="Evaluate a jinja2 template with some CSV data."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        dest="csv_filename",
        help="Path to input csv data",
    )
    parser.add_argument(
        "-o",
        "--output",
        required=True,
        dest="output_filename",
        help="Path to output html data",
    )
    parser.add_argument(
        "-t",
        "--template",
        required=True,
        dest="template_filename",
        help="Path to jinja2 template",
    )
    parser.add_argument(
        "-k",
        "--sort_key",
        dest="sort_keys",
        help="Sort key(s) for data",
        action="append",
    )
    parser.add_argument(
        "--join_csv",
        dest="join_csv",
        help="CSV file of data to join with main CSV input",
    )
    parser.add_argument(
        "--join_lkey",
        dest="join_lkey",
        help="Column name of key in input CSV to lookup for join.",
    )
    parser.add_argument(
        "--join_rkey",
        dest="join_rkey",
        help="Column name of key in join CSV to lookup for join.",
    )
    parser.add_argument(
        "--join_value",
        dest="join_value",
        help="Column name for the value in join_csv to add to the CSV input",
    )
    parser.add_argument(
        "-w", "--wp_upload_url", dest="wp_upload_url", help="URL for wp-JSON upload."
    )

    args = parser.parse_args()

    if args.wp_upload_url:
        wp_user = os.getenv("TEMPLATER_WP_USER")
        if not wp_user:
            raise Exception(
                "WP Upload URL specified but TEMPLATER_WP_USER not in environment."
            )
        wp_asp = os.getenv("TEMPLATER_WP_ASP")
        if not wp_asp:
            raise Exception(
                "WP Upload URL specified but TEMPLATER_WP_ASP not in environment."
            )

    if args.join_csv:
        if not args.join_lkey or not args.join_rkey or not args.join_value:
            raise Exception(
                "Must specify join_lkey and join_rkey and join_value if join_csv is specified."
            )

    with open(args.csv_filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # There simply won't be that many rows in anything
        # we care to render to a single page. And we might need
        # to go through it twice... materialize!
        data = sort_csv_data(reader, args.sort_keys)
        if args.join_csv:
            with open(args.join_csv, "r", encoding="utf-8") as jf:
                jreader = csv.DictReader(jf)
                join_data(
                    data, jreader, args.join_lkey, args.join_rkey, args.join_value
                )

        content = render_template(args.template_filename, data)

    with open(args.output_filename, "w", encoding="utf-8") as f:
        f.write(content)

    if args.wp_upload_url:
        # Let's hope the UTF-8 encoding works right here!
        update_wp_page(args.wp_upload_url, wp_user, wp_asp, content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
