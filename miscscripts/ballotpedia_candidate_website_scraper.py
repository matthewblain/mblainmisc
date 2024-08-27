# Candidate info scraper
# Goes through a list of candidates on ballotpedia to get some basic info
# mblain 27aug2024


import csv
import re
import sys
import time
from bs4 import BeautifulSoup
import requests

party_re = re.compile(" Party")
candidate_re = re.compile("Candidate, ")
website_re = re.compile("Campaign website")

sleeptime = 0.1  # seconds to sleep between each candidate

# Get the website content for a specific candidate
# e.g. LoadCandidateData('https://ballotpedia.org/Tenessa_Audette')
def LoadCandidateData(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    result = {}
    result["ballotpedia"] = url

    # Let's find the person
    # <div class="infobox person">
    person_div = soup.find("div", attrs={"class": "infobox person"})
    # First div should be the candidate name
    name_div = person_div.find("div")
    result["name"] = name_div and name_div.get_text()
    # <a href="https://ballotpedia.org/Republican_Party">Republican Party</a>
    party_elem = person_div.find("a", string=party_re)
    result["party"] = party_elem and party_elem.get_text()
    candidate_p = person_div.find("p", string=candidate_re)
    result["position"] = candidate_p and candidate_p.get_text().strip()
    website_a = person_div.find("a", string=website_re)
    result["candidate_website"] = website_a and website_a["href"]

    return result


# From a page about a race, get all the 'candidates' listed.
#    E.g. https://ballotpedia.org/California_State_Assembly_elections,_2024
def GetCandidateUrls(url):
    response = requests.get(url)
    soup = BeautifulSoup(response.content, "html.parser")

    # We're looking for something like this
    # We want to find the first candidate table--not both the general and primary.
    candidate_table = soup.find(
        "table",
        attrs={"class": "wikitable sortable collapsible candidateListTablePartisan"},
    )
    # Then find all the candidates
    # <span class="candidate"><a href="https://ballotpedia.org/Tenessa_Audette">Tenessa Audette</a><br></span>
    candidates = candidate_table.find_all("span", attrs={"class": "candidate"})
    results = []
    for c_span in candidates:
        c_a = c_span.find("a")
        results.append(c_a["href"])

    return results


# From a list of pages about particular candidates, get the info about each one
def GetAllCandidateInfo(candidate_urls):
    results = []
    i = 0
    for url in candidate_urls:
        i = i + 1
        print("%d: %s" % (i, url))
        results.append(LoadCandidateData(url))
        time.sleep(sleeptime)

    return results


# Usage:
# scraper "https://ballotpedia.org/California_State_Assembly_elections,_2024" "asm.csv"
def main():
    race_url = sys.argv[1]
    output_filename = sys.argv[2]
    print(race_url)
    candidate_urls = GetCandidateUrls(race_url)
    print("Found %d candidates" % len(candidate_urls))
    all_info = GetAllCandidateInfo(candidate_urls)
    # print(all_info)
    with open(output_filename, "w", encoding="utf-8") as f:
        writer = csv.DictWriter(f, ["position", "name", "party", "ballotpedia", "candidate_website"])
        writer.writeheader()
        writer.writerows(all_info)
    return 0


if __name__ == "__main__":
    sys.exit(main())
