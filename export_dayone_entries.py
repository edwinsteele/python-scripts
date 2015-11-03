"""
Generates a set of standalone markdown files from DayOne entries.

Assumes that this script is run on a Mac that has iCloud Drive Enabled
and DayOne has been setup to Sync with iCloud and that the Folder is
the default, "Journal_dayone".

Requires python 2.7 and the external pytz module.
"""
import argparse
import codecs
import glob
import collections
import plistlib
import pytz
import os
import string
import sys

ENTRY_GLOB_STR = os.path.join(os.environ["HOME"],
                              "Library",
                              "Mobile Documents",
                              "*dayoneapp*",
                              "Documents",
                              "Journal_dayone",
                              "entries",
                              "*.doentry")

Entry = collections.namedtuple(
    'Entry', [
        "title",
        "filename",
        "datestr",
        "tagstr",
        "latitude",
        "longitude",
        "text"
    ]
)


def dayone_entry_files():
    return glob.iglob(ENTRY_GLOB_STR)


def generate_title(document_text):
    first_line = document_text.split("\n")[0]
    # If we have something that looks like a header, use it as a starting
    #  point for a title, otherwise there's no title
    # otherwise don't set a title
    if first_line.startswith("#"):
        # Strip heading indicators and whitespace inside the heading indicators
        title = first_line.lstrip("#").strip()
    else:
        title = ""
    return title


def generate_slug_from_title(title):
    # Make utf-8 so we can use the non-unicode translate function later
    slug = title.encode("utf-8")
    # Generate a pair of strings for a translation table
    # We replace punctuation with a dash
    from_strings = string.punctuation
    to_strings = "-" * len(from_strings)
    # Also translate spaces to dashes
    from_strings = " " + from_strings
    to_strings = "-" + to_strings
    slugify_table = string.maketrans(from_strings, to_strings)
    slug = slug.translate(slugify_table)
    # Make lowercase so the slug is neater
    slug = slug.lower()
    # Strip leading ex-punctuation so the slug reads better
    # This neatens things like trailing question-marks
    slug = slug.strip("-")
    # Collapse duplicate dashes into a single dash
    slug = "-".join([each for each in slug.split("-") if each])
    return slug


def extract_one_file(input_file):
    p = plistlib.readPlist(input_file)
    authored_tz = pytz.timezone(p["Time Zone"])
    # Creation date stored in zulu time
    creation_date_utc = pytz.utc.localize(p["Creation Date"])
    creation_date_local = creation_date_utc.astimezone(authored_tz)
    title = generate_title(p["Entry Text"])
    slug = generate_slug_from_title(title)
    if slug:
        filename = "%s_%s.md" % \
            (creation_date_local.strftime("%Y%m%d-%H%M"), slug)
    else:
        filename = "%s.md" % \
            (creation_date_local.strftime("%Y%m%d-%H%M"),)
    if "Tags" in p:
        tagstr = ",".join(sorted(p["Tags"]))
    else:
        tagstr = ""

    if "Location" in p:
        lat = p["Location"]["Latitude"]
        lon = p["Location"]["Longitude"]
    else:
        lat = lon = None

    return Entry(title,
                 filename,
                 creation_date_local.ctime(),
                 tagstr,
                 lat,
                 lon,
                 p["Entry Text"])


def convert_entry_to_str(entry):
    # Metadata lines have two trailing spaces to help with formatting
    # per: https://github.com/fletcher/MultiMarkdown/wiki/MultiMarkdown-Syntax-Guide
    lines = []
    if entry.title:
        lines.append("Title: %s  " % (entry.title,))
    lines.append("Date: %s  " % (entry.datestr,))
    if entry.tagstr:
        lines.append("Tags: %s  " % (entry.tagstr,))
    if entry.latitude:
        lines.append("Latitude: %s  " % (entry.latitude,))
    if entry.longitude:
        lines.append("Longitude: %s  " % (entry.longitude,))
    lines.append("")
    lines.append(entry.text)
    return "\n".join(lines)


def write_one_entry(entry, output_directory):
    output_file = os.path.join(output_directory, entry.filename)
    if os.path.exists(output_file):
        print "Error: Entry already exists %s. " \
              "Delete it and try again." % (output_file,)
        sys.exit(2)
    print "Writing: %s" % (output_file,)
    with codecs.open(output_file, "w", encoding="utf-8") as f:
        f.write(convert_entry_to_str(entry))


def main():
    parser = argparse.ArgumentParser(
        description="Convert DayOne entries into Markdown files.")
    parser.add_argument("output_directory")
    args = parser.parse_args()

    # Check output directory is useable.
    if os.path.exists(args.output_directory):
        if not os.path.isdir(args.output_directory):
            print "Error: %s exists but is not a directory. " \
                  "Fix this and try again." % (args.output_directory,)
            sys.exit(1)
    else:
        print "Error: Directory %s does not exist. " \
              "Create it and try again." % (args.output_directory,)
        sys.exit(1)

    for entry_file in dayone_entry_files():
        one_entry = extract_one_file(entry_file)
        write_one_entry(one_entry, args.output_directory)

if __name__ == "__main__":
    main()
