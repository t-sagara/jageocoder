import csv
import json
import logging
import os
import sys
import time
import unittest

import jageocoder

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


class TestSearchMethods(unittest.TestCase):

    def setUp(self):
        dbpath = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../db/address.db'))
        triepath = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../db/address.trie'))
        jageocoder.init(dsn="sqlite:///" + dbpath, trie_path=triepath)

    def test_sapporo(self):
        """
        Test a notation which is omitting '条' in Sapporo city.
        """
        query = '札幌市中央区北3西1-7'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '札幌市中央区北3西1-7')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(
            top['fullname'],
            ['北海道', '札幌市', '中央区', '北三条西', '一丁目', '7番地'])

    def test_akita(self):
        query = '秋田市山王4-1-1'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '秋田市山王4-1-')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(top['fullname'],
                         ['秋田県', '秋田市', '山王', '四丁目', '1番'])

    def test_kyoto(self):
        """
        Test a notation which is containing street name in Kyoto city.
        """
        query = '京都市上京区下立売通新町西入薮ノ内町'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '京都市上京区下立売通新町西入薮ノ内町')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 5)
        self.assertEqual(top['fullname'],
                         ['京都府', '京都市', '上京区', '藪之内町'])

    def test_oaza(self):
        """
        Test notations with and without "大字"
        """
        query = '東京都西多摩郡瑞穂町大字箱根ケ崎2335番地'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '東京都西多摩郡瑞穂町大字箱根ケ崎2335番地')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(top['fullname'],
                         ['東京都', '西多摩郡', '瑞穂町', '箱根ケ崎', '2335番地'])

        query = '東京都西多摩郡瑞穂町箱根ケ崎2335番地'
        result = jageocoder.search(query)
        self.assertEqual(result['matched'], '東京都西多摩郡瑞穂町箱根ケ崎2335番地')
        candidates = result['candidates']
        self.assertEqual(len(candidates), 1)
        top = candidates[0]
        self.assertEqual(top['level'], 7)
        self.assertEqual(top['fullname'],
                         ['東京都', '西多摩郡', '瑞穂町', '箱根ケ崎', '2335番地'])
