import csv
import json
import logging
import os
import time
import unittest

from jageocoder.address import AddressNode, AddressTree

logger = logging.getLogger(__name__)

class TestSearchMethods(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.INFO)
        dbpath = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../db/all_latlon.db'))
        triepath = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../db/all_latlon.trie'))
        self.tree = AddressTree(dsn="sqlite:///" + dbpath,
                                trie=triepath, debug=False)

    def test_akita(self):
        query = '秋田市山王4-1-1-'
        result = self.tree.search(query)
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0].as_dict()
        self.assertEqual(top['level'], 7)
        self.assertEqual(top['fullname'],
                         ['秋田県', '秋田市', '山王', '四丁目', '１番'])
