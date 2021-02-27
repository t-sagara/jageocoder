import csv
import json
import logging
import os
import sys
import time
import unittest

from jageocoder.address import AddressNode, AddressTree

logger = logging.getLogger(__name__)

class TestSearchMethods(unittest.TestCase):

    def setUp(self):
        logging.basicConfig(level=logging.INFO)
        dbpath = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../db/isj.db'))
        triepath = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../db/isj.trie'))
        self.tree = AddressTree(dsn="sqlite:///" + dbpath,
                                trie=triepath, debug=False)

    def test_sapporo(self):
        query = '札幌市中央区北3西1-7-'
        result = self.tree.search(query)
        self.assertEqual(result['matched'], '札幌市中央区北3西1-7-')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0].as_dict()
        self.assertEqual(top['level'], 7)
        self.assertEqual(
            top['fullname'],
            ['北海道', '札幌市', '中央区', '北三条西', '一丁目', '7番地'])
        
    def test_akita(self):
        query = '秋田市山王4-1-1-'
        result = self.tree.search(query)
        self.assertEqual(result['matched'], '秋田市山王4-1-')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0].as_dict()
        self.assertEqual(top['level'], 7)
        self.assertEqual(top['fullname'],
                         ['秋田県', '秋田市', '山王', '四丁目', '1番'])


    def test_kyoto(self):
        query = '京都市上京区下立売通新町西入薮ノ内町'
        result = self.tree.search(query)
        self.assertEqual(result['matched'], '京都市上京区下立売通新町西入薮ノ内町')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0].as_dict()
        self.assertEqual(top['level'], 5)
        self.assertEqual(top['fullname'],
                         ['京都府', '京都市', '上京区', '藪之内町'])
