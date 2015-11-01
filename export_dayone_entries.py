"""
Generates a set of standalone markdown files from DayOne entries.

Assumes that this script is run on a Mac that has iCloud Drive Enabled
and DayOne has been setup to Sync with iCloud and that the Folder is
the default, "Journal_dayone".

Requires python 2.7 and the external pytz module.
"""
import argparse
import glob
import plistlib
import pytz
import os
import string

ENTRY_GLOB_STR = os.path.join(os.environ["HOME"],
                              "Library",
                              "Mobile Documents",
                              "*dayoneapp*",
                              "Documents",
                              "Journal_dayone",
                              "entries",
                              "*.doentry")


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


def convert_one_file(input_file):
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
    print "--- FILE: %s ---" % (filename,)
    if title:
        print "Title: %s" % (title,)
    print "Date: %s" % (creation_date_local.ctime(),)
    if "Tags" in p:
        print "Tags: %s" % (",".join(sorted(p["Tags"])),)
    if "Location" in p:
        print "Latitude: %s" % (p["Location"]["Latitude"],)
        print "Longitude: %s" % (p["Location"]["Longitude"],)

    print ""
    print p["Entry Text"].split("\n")[0]


def main():
    parser = argparse.ArgumentParser(
        description="Convert DayOne entries into Markdown files.")
    parser.add_argument("output_directory")
    parser.parse_args()
    for entry_file in dayone_entry_files():
        convert_one_file(entry_file)

if __name__ == "__main__":
    main()
