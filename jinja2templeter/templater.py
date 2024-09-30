# Jinja2 CSV template tool.
# 
# This is a really simple tool: It loads a jinja2 template
# and a CSV file and renders the tempalte.
# 
# mblain 27sep2024


import csv
import re
import sys
import time
import jinja2


# Run the template...

def do_stuff(template_filename, csv_data):
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader("."),
        autoescape=jinja2.select_autoescape(),
        lstrip_blocks=True
    )
    try:
        template = env.get_template(template_filename)
    except jinja2.exceptions.TemplateSyntaxError as e:
        print ("%s[%d]: %s" % (e.filename, e.lineno, e.message),  file=sys.stderr)
        #raise e
        return
    
    # {{ row['']  }}
    
    print(template.render(csv_data=csv_data, lastupdated="now"))
    

# Usage:
# templater templatefilename csvfilename > outputfilename
def main():
    template_filename = sys.argv[1]
    csv_filename = sys.argv[2]

    with open(csv_filename, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        do_stuff(template_filename, reader)
        
    return 0


if __name__ == "__main__":
    sys.exit(main())
