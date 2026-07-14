import csv
import xml.etree.ElementTree as ET
from collections import Counter

# MARC XML namespace
NS = {"marc": "http://www.loc.gov/MARC21/slim"}

# Parse the MARC XML file
tree = ET.parse("sources/marc/artists-books-marc.xml")
root = tree.getroot()

print("XML loaded successfully!")


def clean_value(value):
    """Remove surrounding whitespace and trailing periods."""
    if value is None:
        return ""
    return value.strip().rstrip(".")


# Count subject fields
tags = {"650": 0, "651": 0, "655": 0}

for field in root.findall(".//marc:datafield", NS):
    tag = field.attrib.get("tag")
    if tag in tags:
        tags[tag] += 1

print("Subject field counts:")
print(tags)

# Store all extracted subject headings
subjects = []

for field in root.findall(".//marc:datafield", NS):

    tag = field.attrib.get("tag")

    if tag not in {"650", "651", "655"}:
        continue

    heading_parts = []
    vocabulary = ""
    uri = ""

    for subfield in field.findall("marc:subfield", NS):

        code = subfield.attrib["code"]
        text = clean_value(subfield.text)

        # Build the complete heading
        if code in {"a", "x", "y", "z", "v"}:
            heading_parts.append(text)

        # Vocabulary explicitly stored in $2
        elif code == "2":
            vocabulary = text.lower()

        # URI stored in $0
        elif code == "0":
            uri = text

    heading = " -- ".join(heading_parts)

    # Infer vocabulary from MARC indicator for 650 fields
    if tag == "650" and not vocabulary:

        ind2 = field.attrib.get("ind2")

        if ind2 == "0":
            vocabulary = "lcsh"
        elif ind2 == "1":
            vocabulary = "lcshac"
        elif ind2 == "2":
            vocabulary = "mesh"
        elif ind2 == "3":
            vocabulary = "nal"
        elif ind2 == "4":
            vocabulary = "unspecified"
        elif ind2 == "5":
            vocabulary = "csh"
        elif ind2 == "6":
            vocabulary = "rvm"

    # Optional data quality check Ryan mentioned
    if tag == "650":

        ind2 = field.attrib.get("ind2")

        if ind2 == "0" and vocabulary not in {"", "lcsh"}:
            print("\nPotential inconsistency:")
            print("Heading:", heading)
            print("Vocabulary:", vocabulary)

    # Append EVERY subject record
    subjects.append(
        {
            "tag": tag,
            "heading": heading,
            "vocabulary": vocabulary,
            "uri": uri,
        }
    )

print(f"\nExtracted {len(subjects)} subject headings.")

# Show a few examples
print("\nFirst 10 extracted subjects:")
for subject in subjects[:10]:
    print(subject)

# Count unique combinations
subject_counts = Counter(
    (
        subject["tag"],
        subject["vocabulary"],
        subject["uri"],
        subject["heading"],
    )
    for subject in subjects
)

# Count second indicators for 650 fields
indicator_counts = Counter()

for field in root.findall(".//marc:datafield", NS):
    if field.attrib.get("tag") == "650":
        ind2 = field.attrib.get("ind2", " ")
        indicator_counts[ind2] += 1

print("\n650 second indicator counts:")
for ind2, count in sorted(indicator_counts.items()):
    print(f"ind2='{ind2}': {count}")

# Export CSV
output_file = "subject_headings.csv"

with open(output_file, "w", newline="", encoding="utf-8") as csvfile:

    fieldnames = [
        "tag",
        "vocabulary",
        "uri",
        "heading",
        "count",
    ]

    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

    writer.writeheader()

    for (tag, vocabulary, uri, heading), count in sorted(subject_counts.items()):

        writer.writerow(
            {
                "tag": tag,
                "vocabulary": vocabulary,
                "uri": uri,
                "heading": heading,
                "count": count,
            }
        )

print(f"\nWrote {len(subject_counts)} unique subject headings to {output_file}")