"""
Return language information from the database - "langinfo.csv"

Usage:
    GetLanguage.py langname format
Where:
    langname is the 3 letter identifier e.g. deu, fra, jpn, kor, etc
    format is one of the headers from langinfo.csv, e.g. dotnet, hex_lcid, etc.
"""

import os
import csv


def ReadLangInfoDB(lang_info_filepath = None):
    "Load the CSV file with the language information"

    # if no file specified then default to langinfo.csv in the same
    # folder as the script
    if lang_info_filepath is None:
        lang_info_filepath = os.path.join(
            os.path.dirname(__file__), 'langinfo.csv')

    # open the file and initialize the CSV DictReader
    lang_info_file = open(lang_info_filepath, "rb")
    # skip leading comments and blank lines
    while True:
        line_start = lang_info_file.tell()
        line = lang_info_file.readline()
        if line.strip() and not line.strip().startswith(';'):
            lang_info_file.seek(line_start)
            break

    csv_reader = csv.DictReader(lang_info_file)

    # each entry from DictReader will be a dictionary
    #
    lang_info = {}
    for line in csv_reader:
        line['culture'] = line['dotnet'][:2]
        lang_info[line['lang'].lower()] = line

    lang_info_file.close()

    return lang_info


def GetLangInfo(lang, requested_format):
    "Return  the information "

    languages_db = ReadLangInfoDB()

    if lang not in languages_db:
        raise RuntimeError ("Unknown language: '%s' Known languages: %s"%
            (lang, ", ".join(languages_db.keys()) ) )

    language_data = languages_db[lang]

    if requested_format not in language_data:
        raise RuntimeError ("Unknown format: '%s' Known formats: %s"%
            (requested_format, ", ".join(language_data.keys()) ) )

    return language_data[requested_format]

if __name__ == "__main__":
    import sys

    try:
        req_lang = sys.argv[1].lower()
        req_format = sys.argv[2].lower()
    except IndexError:
        print __doc__
        sys.exit(1)

    try:
        lang_info = GetLangInfo(req_lang, req_format)
        if not lang_info.strip():
            print "Language '%s' has no setting for '%s'" % (
                req_lang, req_format)
            sys.exit(2)
        print lang_info
    except RuntimeError, e:
        print e
        sys.exit(1)

    # successfully done
    sys.exit(0)

