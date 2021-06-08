"""LHH Wayfiding Sign generator.

Takes a SVG-ish template file and a CSV with trail sign descrptions.
Genrates an SVG per trail sign.

CSV file must have headers with columns SignID, TrailName, Arrow
Arrow must be one of  S,L,R,BL,BR,LR,V.



Todo: Use CSS or SVG/DOM instead of horrid search/replace templating.
Todo: Use Inkscape to generate the PDF files.


Matthew Blain, 04jun2021
"""

import csv
import sys


def generate_files(template_text, csv_data, output_base):
    seen_ids = set()
    for sign_info in csv_data:
        if sign_info["SignID"] in seen_ids:
            raise Exception("Sign ID seen more than once: " + sign_info["SignID"])
        result = fill_template(template_text, sign_info)
        sign_filename = output_base + sign_info['SignID'] + ".svg"
        with open(sign_filename, "w") as f:
            f.writelines(result)


def fill_template(template_text, sign_info):
    # TODO: Use a real template system.
    result = template_text.replace("TRAILNAMETRAILNAME", sign_info["TrailName"])
    print(sign_info)
    a = sign_info["Arrow"]
    result = result.replace("ARROWUPSTYLE", "" if a == 'S' else "display:none")
    result = result.replace("ARROWLEFTSTYLE", "" if a == 'L' else "display:none")
    result = result.replace("ARROWRIGHTSTYLE", "" if a == 'R' else "display:none")
    result = result.replace("ARROWUPLEFTSTYLE", "" if a == 'BL' else "display:none")
    result = result.replace("ARROWUPRIGHTSTYLE", "" if a == 'BR' else "display:none")
    result = result.replace("ARROWLEFTRIGHTSTYLE", "" if a == 'LR' else "display:none")
    result = result.replace("ARROWVSTYLE", "" if a == 'V' else "display:none")    
    return result


def template_to_svg(template_filename, csv_filename, output_path_base):
    with open(template_filename, "r") as r:
        template = r.read()  # Hope it's short enough for a single read!
    with open(csv_filename, "r") as r:
        csv_data = csv.DictReader(r)
        generate_files(template, csv_data, output_path_base)


def main(argv):
    template_to_svg(argv[1], argv[2], argv[3])


if __name__ == "__main__":
    main(sys.argv)
