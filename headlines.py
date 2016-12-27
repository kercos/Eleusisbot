# -*- coding: utf-8 -*-

import urllib2
import icons
import csv

DOC_KEY = '18FE0TpjK138K8aOmq2YSqFCth0W3gIgAqR4iwZhdkKg'
GDOC_TSV_BASE_URL = "https://docs.google.com/spreadsheets/d/{0}/export?format=tsv&gid={1}"

GID_LEGITIMATE = 0
GID_ILLEGITIMATE = 1886840090

def getHeadlines():
    result = [] # legitimate and illegitimmate ORDERED array
    legitimate_url = GDOC_TSV_BASE_URL.format(DOC_KEY, GID_LEGITIMATE)
    illegitimate_url = GDOC_TSV_BASE_URL.format(DOC_KEY, GID_ILLEGITIMATE)
    for url in [legitimate_url, illegitimate_url]:
        spreadSheetTsv = urllib2.urlopen(url)
        spreadSheetReader = csv.reader(spreadSheetTsv, delimiter='\t', quoting=csv.QUOTE_NONE)
        lines = []
        for row in spreadSheetReader:
            lines.append(row[0])
        result.append(lines)
    return result

HEADLINES = getHeadlines()
LEGITIMATE_HEADLINES,  ILLEGITIMATE_HEADLINES = HEADLINES

def getLegitimateHeadlines():
    return LEGITIMATE_HEADLINES

def getIllegitimateHeadlines():
    return ILLEGITIMATE_HEADLINES
