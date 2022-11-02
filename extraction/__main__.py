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


def get_cic_data(filename):
    cic36_page = None
    results = {}
    with pdfplumber.open(filename) as pdf:
        for page in tqdm(pdf.pages):
            page_text = page.extract_text()
            if SEARCH_REGEX.search(page_text):
                cic36_page = page.page_number

        for area, bbox, offset in AREAS:
            if cic36_page:
                page = pdf.pages[cic36_page + offset - 1]
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


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("input", help="Input ZIP files")
    parser.add_argument("output", help="Output CSV file")
    args = parser.parse_args()

    files = glob.iglob(args.input)

    output_mode = "w"
    if os.path.exists(args.output):
        output_mode = "a"

    with open(args.output, output_mode, newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=[
                "zip_filename",
                "pdf_filename",
                "timestamp",
                "status",
                "company_number",
                "community_interest_statement",
                "activities",
                "community_benefit",
            ],
        )
        if output_mode == "w":
            writer.writeheader()
        timestamp = datetime.now().isoformat()
        for file in files:

            if file.endswith(".pdf"):

                result = {
                    "zip_filename": None,
                    "pdf_filename": file,
                    "timestamp": timestamp,
                    "status": "no data found",
                }
                company_number_search = COMPANY_NUMBER_REGEX.search(
                    result["pdf_filename"]
                )
                if company_number_search:
                    result["company_number"] = company_number_search.group(0)
                result.update(get_cic_data(file))
                if (
                    result.get("community_interest_statement")
                    or result.get("activities")
                    or result.get("community_benefit")
                ):
                    result["status"] = "success"

                writer.writerow(result)
                continue

            try:
                with ZipFile(file, mode="r") as zip:
                    for index, name in tqdm(enumerate(zip.namelist())):
                        if not name.endswith(".pdf"):
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

                        writer.writerow(result)

                        if index > 10:
                            break
            except BadZipFile:
                print(f"Bad ZIP file: {file}")


if __name__ == "__main__":
    main()
