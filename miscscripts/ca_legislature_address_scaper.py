# Aassembly Address Scraper
# Goes through all the assembly districts and reads the "Address" div.
# And maybe the senata too.
# mblain 2jul2024

# this script is silly, it should just scrape this:
# https://www.assembly.ca.gov/assemblymembers
# But I found the individual one first.

import re
import sys 
from bs4 import BeautifulSoup
import requests

p_o_box_re = string=re.compile("P.O. Box")   # yeah escape the .

# Get the website content
def LoadUrlData(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    address_div = soup.find("div", attrs={"class": "address"})
    # Extract the content of the meta description tag (if it exists)
    if address_div:
        po_box = address_div.find(string=p_o_box_re)
        if po_box:
           return (po_box.get_text())
        else:
           print (address_div)
           return ("address-no-po-box")
    else:
        return ("no-address")
        



# There are 80 legislators.
def GetAllLegInfo():
    for district in range(1,81):
        url = ('https://www.assembly.ca.gov/assemblymembers/%02d' % district)
        address = LoadUrlData(url)
        print ("AD%02d\t%s" % (district, address))
        
        
def main():
    GetAllLegInfo()
    return (0)
    
if __name__ == '__main__':
    sys.exit(main())
