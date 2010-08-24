"""
Return language information from the 'database' langinfo.csv



"""

import sys
import os
import csv

##class Langauge(object):
##    def __init__(self, data):
##        self.data = data
##        
##        self.data['culture'] = self.dotnet[:2]
##
##    def __getattr__(self, attr):
##        return self[attr]
##        
##    def __getitem__(self, attr):
##        # if the attribute requested is a key in the dictionary
##        if attr in self.data:
##            return self.data[attr]
##        
##            
##        # is the attribute all upper case and the lower case in the data
##        elif attr == attr.upper() and attr.lower() in self.data:
##            # then return the value upper cased
##            return self.data[attr.lower()].upper()
##        
##        # not an attribute we know about - raise an error
##        raise AttributeError(
##            "Language has no attribute: '%s' - %s"% (attr, self.data.keys()))
##


def ReadLangInfoDB(lang_info_filepath = None):
    # if no file specified then default to langinfo.csv in the same 
    # folder as the script
    if lang_info_filepath is None:
        lang_info_filepath = os.path.join(
            os.path.dirname(__file__), 'langinfo.csv')        
    
    # open the file and initialize the CSV DictReader 
    lang_info_file = open(lang_info_filepath, "rb")
    csv_reader = csv.DictReader(lang_info_file)
    
    # each entry from DictReader will be a dictionary
    # 
    lang_info = {}
    for line in csv_reader:
        line['culture'] = line['dotnet'][:2]
        lang_info[line['lang'].lower()] = line
        

    lang_info_file.close()

    return lang_info   


if __name__ == "__main__":
    
    lang = sys.argv[1].lower()
    format = sys.argv[2].lower()

    languages_db = ReadLangInfoDB()
    
    if lang not in languages_db:
        print "Unknown language: '%s'"% lang
        print "Known languages: %s"% ", ".join(languages_db.keys())
        sys.exit(1)

    language_data = languages_db[lang]
    
    if format not in language_data:
        print "Unknown format: '%s'"% format
        print "Known formats: %s"% ", ".join(language_data.keys())
        sys.exit(1)
    
    print language_data[format]
    
    # successfully done
    sys.exit(0)
 
