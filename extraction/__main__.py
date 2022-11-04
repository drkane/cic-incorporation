import argparse
import csv
from datetime import datetime
import glob
import os
import re
from zipfile import ZipFile, BadZipFile

import pdfplumber
from tqdm import tqdm

SEARCH_REGEX = re.compile(r"CIC[ ]+36|Declarations on Formation")

# from https://gist.github.com/rob-murray/01d43581114a6b319034732bcbda29e1
COMPANY_NUMBER_REGEX = re.compile(
    r"\b((AC|ZC|FC|GE|LP|OC|SE|SA|SZ|SF|GS|SL|SO|SC|ES|NA|NZ|NF|GN|NL|NC|R0|NI|EN|\d{2}|SG|FE)\d{5}(\d|C|R))|((RS|SO)\d{3}(\d{3}|\d{2}[WSRCZF]|\d(FI|RS|SA|IP|US|EN|AS)|CUS))|((NI|SL)\d{5}[\dA])|(OC(([\dP]{5}[CWERTB])|([\dP]{4}(OC|CU))))\b"
)

AREAS = (
    (
        "community_interest_statement",
        (
            0.192,  # x0,
            0.474,  # top,
            0.920,  # x1,
            0.836,  # bottom,
        ),
        0,
    ),
    (
        "activities",
        (
            0.074,  # x0,
            0.346,  # top,
            0.357,  # x1,
            0.645,  # bottom,
        ),
        1,
    ),
    (
        "community_benefit",
        (
            0.357,  # x0,
            0.346,  # top,
            0.927,  # x1,
            0.645,  # bottom,
        ),
        1,
    ),
)

CSV_FIELDS = [
    "zip_filename",
    "pdf_filename",
    "timestamp",
    "status",
    "company_number",
    "community_interest_statement",
    "activities",
    "community_benefit",
]


def get_cic_data(filename):
    cic36_page = None
    results = {}
    with pdfplumber.open(filename) as pdf:
        for page in tqdm(pdf.pages):
            page_text = page.extract_text()
            if SEARCH_REGEX.search(page_text):
                cic36_page = page.page_number
                break

        for area, bbox, offset in AREAS:
            if cic36_page:
                page_number = cic36_page + offset - 1
                try:
                    page = pdf.pages[page_number]
                except IndexError:
                    continue
                crop = page.crop(
                    (
                        bbox[0] * page.width,  # x0,
                        bbox[1] * page.height,  # top,
                        bbox[2] * page.width,  # x1,
                        bbox[3] * page.height,  # bottom,
                    )
                )
                results[area] = " ".join(crop.extract_text().split("\n"))

    return results


def write_results(results, filename):
    with open(filename, "a", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=CSV_FIELDS,
        )
        writer.writerow(results)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input ZIP files")
    parser.add_argument("output", help="Output CSV file")
    parser.add_argument(
        "--test",
        help="Number of files to run on (if 0 or none then will use all files)",
        default=None,
        type=int,
    )
    parser.add_argument(
        "--skip-existing",
        help="Skip existing files",
        action=argparse.BooleanOptionalAction,
    )
    args = parser.parse_args()

    files = glob.glob(args.input)

    print(f"Found {len(files)} files")

    if not os.path.exists(args.output):
        with open(args.output, "w", newline="") as output:
            writer = csv.DictWriter(
                output,
                fieldnames=CSV_FIELDS,
            )
            writer.writeheader()

    if args.skip_existing:
        existing_files = set()
        with open(args.output, "r", newline="") as output:
            reader = csv.DictReader(output)
            for row in reader:
                existing_files.add(os.path.abspath(row["pdf_filename"]))

    count_files = 0

    timestamp = datetime.now().isoformat()
    for file in files:

        if args.test and count_files >= args.test:
            break

        if file.endswith(".pdf"):

            if args.skip_existing and os.path.abspath(file) in existing_files:
                continue

            result = {
                "zip_filename": None,
                "pdf_filename": file,
                "timestamp": timestamp,
                "status": "no data found",
            }
            company_number_search = COMPANY_NUMBER_REGEX.search(result["pdf_filename"])
            if company_number_search:
                result["company_number"] = company_number_search.group(0)
            result.update(get_cic_data(file))
            if (
                result.get("community_interest_statement")
                or result.get("activities")
                or result.get("community_benefit")
            ):
                result["status"] = "success"

            write_results(result, args.output)
            count_files += 1
            continue

        try:
            with ZipFile(file, mode="r") as zip:
                for index, name in tqdm(enumerate(zip.namelist())):
                    if not name.endswith(".pdf"):
                        continue

                    if args.skip_existing and os.path.abspath(name) in existing_files:
                        continue

                    result = {
                        "zip_filename": file,
                        "pdf_filename": name,
                        "timestamp": timestamp,
                        "status": "no data found",
                    }
                    company_number_search = COMPANY_NUMBER_REGEX.search(
                        result["pdf_filename"]
                    )
                    if company_number_search:
                        result["company_number"] = company_number_search.group(0)
                    with zip.open(name) as pdf:
                        result.update(get_cic_data(pdf))
                    if (
                        result.get("community_interest_statement")
                        or result.get("activities")
                        or result.get("community_benefit")
                    ):
                        result["status"] = "success"

                    write_results(result, args.output)
                    count_files += 1

                    if args.test and count_files >= args.test:
                        break
        except BadZipFile:
            print(f"Bad ZIP file: {file}")


if __name__ == "__main__":
    main()
