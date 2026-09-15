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
#  templater template_filename csv_data output_filename [Wordpress endpoint]
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


# Usage:
# templater templatefilename csvfilename > outputfilename
def main():
    template_filename = sys.argv[1]
    csv_filename = sys.argv[2]
    output_filename = sys.argv[3]
    wp_upload_url = len(sys.argv) > 4 and sys.argv[4] or ""

    if wp_upload_url:
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

    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # There simply won't be that many rows in anything
        # we care to render to a single page. And we might need
        # to go through it twice... materialize!
        data = list(reader)
        content = render_template(template_filename, data)

    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(content)

    if wp_upload_url:
        # Let's hope the UTF-8 encoding works right here!
        update_wp_page(wp_upload_url, wp_user, wp_asp, content)

    return 0


if __name__ == "__main__":
    sys.exit(main())
