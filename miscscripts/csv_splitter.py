"""
CSV File splitter.

Result of asking Google Gemeni for this:

here's a  simpla csv task: given a CSV file with headers,
let's say with a column called "Team", I want it to go through the CSV file and
create multple new CSV file where each file has the filename based on the value
 of Team and each file will contain only the rows with one value of Team.
"""

import csv
import sys
from collections import defaultdict


def split_csv_by_column(input_file, split_column):
    """Splits a CSV file into multiple CSV files based on unique values in a specified column.

    Args:
        input_file (str): Path to the source CSV file.
        split_column (str): The column header name to group and split by (e.g., 'Team').
    """
    grouped_rows = defaultdict(list)

    try:
        with open(input_file, mode="r", encoding="utf-8") as infile:
            reader = csv.DictReader(infile)

            # Validate that the requested column exists in the header
            if split_column not in reader.fieldnames:
                print(
                    f"Error: Column '{split_column}' not found in '{input_file}'.",
                    file=sys.stderr,
                )
                print(
                    f"Available columns: {', '.join(reader.fieldnames)}",
                    file=sys.stderr,
                )
                sys.exit(1)

            headers = reader.fieldnames

            # Group rows by the value in split_column
            for row in reader:
                team_value = row[split_column].strip()
                if team_value:  # Skip empty team values if necessary
                    grouped_rows[team_value].append(row)

        # Write each group to a new CSV file
        for team_name, rows in grouped_rows.items():
            # Sanitize filename (replaces spaces/special chars if needed)
            safe_team_name = "".join(
                c for c in team_name if c.isalnum() or c in (" ", "_", "-")
            ).rstrip()
            output_file = f"{safe_team_name}.csv"

            with open(output_file, mode="w", newline="", encoding="utf-8") as outfile:
                writer = csv.DictWriter(outfile, fieldnames=headers)
                writer.writeheader()
                writer.writerows(rows)

            print(f"Created '{output_file}' with {len(rows)} rows.")

    except FileNotFoundError:
        print(f"Error: The file '{input_file}' was not found.", file=sys.stderr)
    except Exception as e:
        print(f"An unexpected error occurred: {e}", file=sys.stderr)


def main():
    if len(sys.argv) < 3:
        print(
            "Usage: python split_csv.py <input_csv> <column_name>",
            file=sys.stderr,
        )
        sys.exit(1)

    input_filename = sys.argv[1]
    column_name = sys.argv[2]

    split_csv_by_column(input_filename, column_name)


if __name__ == "__main__":
    main()
