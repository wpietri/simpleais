#!/usr/bin/env python
import json
import os
import re
from collections import OrderedDict

from bs4 import BeautifulSoup


# Takes the AIVDM html file (downloaded from from http://catb.org/gpsd/AIVDM.html) and extracts JSON
# that is used by SimpleAIS to do protocol decoding. This only needs to be re-run when the source
# HTML changes or when expanding parser functionality. When using the library normally, all packet
# info is pulled from the AIVDM.json file.



class Table:
    def __init__(self, soup_table, title_override=None, headings_override=None):
        self.title = title_override or self.extract(soup_table, 'caption')
        self.rows = [self.extract_all(row, 'td') for row in soup_table.find('tbody').find_all('tr')]
        self.headings = headings_override or self.extract_headings(soup_table)

    def extract_headings(self, soup_table):
        result = self.extract_all(soup_table, 'th')
        if result and len(result) > 0:
            return result
        if len(self.rows[0]) == 2:
            return ['key', 'value']

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

    if len(result['member']) == 0:
        result['member'] = 'ignored-' + str(result['start'])

    if 'T' in row:
        result['type'] = row['T']
    elif 'u' in row:
        result['type'] = row['u']
    else:
        raise (ValueError("can't find type in row {}".format(row)))
    return result


def keyify(string):
    string = string.lower()
    return re.sub('\s+', '_', string)


def message_info_for_table(table, name):
    result = OrderedDict()
    result['name'] = name
    result['fields'] = [fields_for_row(row) for row in table.as_list_of_dicts() if not row['Field'] == "?"]
    return result


def lookup_for_table(table):
    result = {}
    for key, value in table.rows:
        if re.match('^\d+$', key):
            result[key] = value
        elif re.match('^\d+-\d+$', key):
            first, last = re.match('(^\d+)-(\d+)$', key).groups()
            for i in range(int(first), int(last) + 1):
                result[i] = value
        else:
            raise ValueError("unexpected lookup: {}={} for table ".format(key, value, table.title))
    return result


def extract_message_types(soup, message_types):
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
    return messages


def extract_lookups(soup):
    lookups = OrderedDict()
    for htmltable in soup.find_all('table'):
        if htmltable.caption:
            caption = htmltable.caption.get_text()
            caption = re.sub('\s*Table \d+\.\s+', '', caption)
            caption = re.sub('Codes for\s+', '', caption)
            # grab the tables we know we use
            if caption in ('Navigation Status', 'Ship Type'):
                table = Table(htmltable, headings_override=['key', 'value'], title_override=caption)
                lookups[keyify(table.title)] = lookup_for_table(table)
    return lookups


soup = BeautifulSoup(open(os.path.join(os.path.dirname(__file__), 'AIVDM.html')), 'html.parser')

message_types = Table(soup.find('h2', {'id': '_ais_payload_interpretation'}).find_next('table'))

messages = extract_message_types(soup, message_types)

# fix errors in source
messages["19"]["fields"][13]["type"] = "e"  # text says (and data confirms) it's an enum
messages["27"]["fields"][6]["type"] = "I1"
messages["27"]["fields"][7]["type"] = "I1"

lookups = extract_lookups(soup)

print(json.dumps({
    'messages': messages,
    'lookups': lookups,
}, indent=4, separators=(',', ': ')))
