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

        # Vocabulary
        elif code == "2":
            vocabulary = text.lower()

        # URI
        elif code == "0":
            uri = text

    heading = " -- ".join(heading_parts)

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