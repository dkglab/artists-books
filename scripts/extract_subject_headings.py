import csv
import xml.etree.ElementTree as ET
from collections import Counter
from collections import defaultdict

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

    # Optional data quality check
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
print(f"\nExtracted {len(subjects)} subject headings.")

uri_map = defaultdict(lambda: {"labels": set(), "vocabularies": set()})
for subject in subjects:
    uri = subject["uri"]
    if not uri:
        continue
    uri_map[uri]["labels"].add(subject["heading"])
    if subject["vocabulary"]:
        uri_map[uri]["vocabularies"].add(subject["vocabulary"])

print("\nURIs with multiple labels:\n")

count = 0
shown = 0

for uri, info in uri_map.items():

    if len(info["labels"]) > 1:

        count += 1

        if shown < 10:
            print(uri)

            for label in sorted(info["labels"]):
                print("  -", label)

            print()

            shown += 1

print(f"Found {count} URIs with multiple labels.")

print("\nURI statistics")

print("Unique URIs:", len(uri_map))

with_uri = sum(1 for s in subjects if s["uri"])

without_uri = len(subjects) - with_uri

print("Subjects with URI:", with_uri)
print("Subjects without URI:", without_uri)

labels_without_uri = Counter()

for subject in subjects:

    if subject["uri"] == "":
        labels_without_uri[subject["heading"]] += 1
print("Unique labels without URI:", len(labels_without_uri))
print("\nMost common labels without URI")

for label, count in labels_without_uri.most_common(20):
    print(count, label)

# Export URI analysis
uri_output = "uri_analysis.csv"

with open(uri_output, "w", newline="", encoding="utf-8") as csvfile:

    fieldnames = [
        "uri",
        "vocabularies",
        "label_count",
        "labels",
    ]

    writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
    writer.writeheader()

    for uri, info in sorted(uri_map.items()):

        writer.writerow(
            {
                "uri": uri,
                "vocabularies": "; ".join(sorted(info["vocabularies"])),
                "label_count": len(info["labels"]),
                "labels": " | ".join(sorted(info["labels"])),
            }
        )

print(f"\nWrote URI analysis to {uri_output}")