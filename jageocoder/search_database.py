import csv
import logging
import os
import time

from jageocoder.address import AddressNode, AddressTree

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    time0 = time.time()

    tree = AddressTree(dsn="sqlite:///db/all_latlon.db", trie="db/all_latlon.trie", debug=False)  # True

    sample_data = os.path.join(
        os.path.dirname(__file__), '../data/pref_office.csv')
    with open(sample_data, 'r', encoding='utf-8', newline='') as f:
        csv = csv.reader(f)
        for rows in csv:
            query = rows[3]
            if query == '都道府県庁所在地':
                continue

            query += '-'
            print("query='{}'".format(query))
            print(tree.search_by_trie(query))
