# Convert the data found in the Secretary of State's PDF of candidate 
# announcements from a vertical form (copy/paste  of text from PDF)
# into a horizontal (TSV) form.
# This is not (yet?) clever enough to align the columns with the 
# types of data, that would be possible but more work.
# There's not real structure to the data, but it is always in the same order.
#
# mblain 27aug2024


import sys


def doStuff(lines):
    in_candidate_section = False
    candidate_info = []
    candidate_number = 0
    results = []

    for line in lines:
        l = line.strip()
        if l == "CANDIDATES FOR NOVEMBER 5, 2024, GENERAL ELECTION":
            # Start of section. Reset data structures and start collecting.
            in_candidate_section = True
            candidate_number = 0
            candidate_info = [[]]
        elif l == "Notice to Candidates":
            # End of section. Print out what we know.
            in_candidate_section = False
            for r in candidate_info[1:]:
                # Position name was seen before anything else.
                r.insert(0, candidate_info[0][0])
                results.append("\t".join(r))
        elif in_candidate_section:
            # The party is after the candidate name. This is how 
            # we identify that it is a [new] candidate.
            if l in [
                "American Independent",
                "Republican",
                "Democratic",
            ]:
                candidate_number += 1
                candidate_info.append([candidate_info[candidate_number - 1].pop()])
            # And now.... append the data!
            candidate_info[candidate_number].append(l)

    return results


def main():
    infile = sys.argv[1]
    outfile = sys.argv[2]

    with open(infile, "r") as i:
        results = doStuff(i)

    with open(outfile, "w") as o:
        o.write("\n".join(results))
    return 0


if __name__ == "__main__":
    sys.exit(main())
