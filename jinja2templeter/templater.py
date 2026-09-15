# Jinja2 CSV template tool.
#
# This is a really simple tool: It loads a jinja2 template
# and a CSV file and renders the tempalte.
#
# mblain 27sep2024


import csv
import os
import re
import sys
import datetime
import jinja2


# Run the template...


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

    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        # There simply won't be that many rows in anything
        # we care to render to a single page. And we might need
        # to go through it twice... materialize!
        data = list(reader)
        result = render_template(template_filename, data)
    
    with open(output_filename, "w", encoding="utf-8") as f:
        f.write(result)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())
