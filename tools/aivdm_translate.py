#!/usr/bin/env python
import os
import re
import json
from collections import OrderedDict

from bs4 import BeautifulSoup


# Takes the AIVDM html file (downloaded from from http://catb.org/gpsd/AIVDM.html) and extracts JSON
# that is used by SimpleAIS to do protocol decoding. This only needs to be re-run when the source
# HTML changes or when expanding parser functionality. When using the library normally, all packet
# info is pulled from the AIVDM.json file.

soup = BeautifulSoup(open(os.path.join(os.path.dirname(__file__), 'AIVDM.html')), 'html.parser')


class Table:
    def __init__(self, soup_table, title_override=None):
        self.title = title_override or self.extract(soup_table, 'caption')
        self.headings = self.extract_all(soup_table, 'th')
        self.rows = [self.extract_all(row, 'td') for row in soup_table.find('tbody').find_all('tr')]

    def extract(self, soup_table, search):
        found = soup_table.find(search)
        if found:
            return found.text.strip()

    def extract_all(self, soup_table, search):
        found = soup_table.find_all(search)
        if found:
            return [f.text.strip() for f in found]

    def as_list_of_dicts(self):
        return [dict(zip(self.headings, row)) for row in self.rows]

    def __getitem__(self, item):
        return self.rows[item]


def fields_for_row(row):
    result = OrderedDict()
    m = re.search("(\d+)-(\d+)", row['Field'])
    if m:
        result['start'] = int(m.group(1))
        result['end'] = int(m.group(2))
    else:
        m = re.search("(\d+)", row['Field'])
        result['start'] = result['end'] = int(m.group(1))
    result['description'] = row['Description']
    if 'Member' in row:
        result['member'] = row['Member']
    elif 'Member/Type' in row:
        result['member'] = row['Member/Type']
    else:
        raise (ValueError("can't find member in row {}".format(row)))
    if 'T' in row:
        result['type'] = row['T']
    elif 'u' in row:
        result['type'] = row['u']
    else:
        raise (ValueError("can't find type in row {}".format(row)))
    return result


def message_info_for_table(table, name):
    result = OrderedDict()
    result['name'] = name
    result['fields'] = [fields_for_row(row) for row in table.as_list_of_dicts() if not row['Field'] == "?"]
    return result


message_types = Table(soup.find('h2', {'id': '_ais_payload_interpretation'}).find_next('table'))

messages = OrderedDict()

for h3 in soup.find_all('h3'):
    if re.search('Types 1, 2 and 3', h3.text):
        cnb_table = Table(h3.find_next('table'))
        messages["1"] = message_info_for_table(cnb_table, message_types[0][1])
        messages["2"] = message_info_for_table(cnb_table, message_types[1][1])
        messages["3"] = message_info_for_table(cnb_table, message_types[2][1])
    match = re.search('Type (\d+):?\s+(.*)', h3.text)
    if match:
        messages[match.group(1)] = message_info_for_table(Table(h3.find_next('table')), match.group(2))

print(json.dumps({'messages': messages}, indent=4, separators=(',', ': ')))
