import logging
import unittest

import jageocoder

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


class TestCodeMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        jageocoder.init(mode='r')
        query = '札幌市中央区北1西2'
        cls.node_sapporo = jageocoder.searchNode(query)[0][0]
        query = '長崎市尾上町３－１'
        cls.node_nagasaki = jageocoder.searchNode(query)[0][0]
        query = '富山市新総曲輪１－７'
        cls.node_toyama = jageocoder.searchNode(query)[0][0]

    def test_pref_name(self):
        """
        Get the names of the prefectures.
        """
        self.assertEqual(self.node_sapporo.get_pref_name(), '北海道')
        self.assertEqual(self.node_nagasaki.get_pref_name(), '長崎県')
        self.assertEqual(self.node_toyama.get_pref_name(), '富山県')

    def test_pref_jiscode(self):
        """
        Get the jiscodes and la code of the prefectures.
        """
        self.assertEqual(
            self.node_sapporo.get_pref_jiscode(), '01')
        self.assertEqual(
            self.node_nagasaki.get_pref_jiscode(), '42')
        self.assertEqual(
            self.node_toyama.get_pref_jiscode(), '16')

    def test_pref_lacode(self):
        """
        Get the local authority codes of the prefectures.
        """
        self.assertEqual(
            self.node_sapporo.get_pref_local_authority_code(),
            '010006')
        self.assertEqual(
            self.node_nagasaki.get_pref_local_authority_code(),
            '420000')
        self.assertEqual(
            self.node_toyama.get_pref_local_authority_code(),
            '160008')

    def test_city_name(self):
        """
        Get the names of the cities.
        """
        self.assertEqual(self.node_sapporo.get_city_name(), '中央区')
        self.assertEqual(self.node_nagasaki.get_city_name(), '長崎市')
        self.assertEqual(self.node_toyama.get_city_name(), '富山市')

    def test_city_jiscode(self):
        """
        Get the jiscodes of the cities.
        """
        self.assertEqual(
            self.node_sapporo.get_city_jiscode(), '01101')
        self.assertEqual(
            self.node_nagasaki.get_city_jiscode(), '42201')
        self.assertEqual(
            self.node_toyama.get_city_jiscode(), '16201')

    def test_city_lacode(self):
        """
        Get the local authority codes of the cities.
        """
        self.assertEqual(
            self.node_sapporo.get_city_local_authority_code(),
            '011011')
        self.assertEqual(
            self.node_nagasaki.get_city_local_authority_code(),
            '422011')
        self.assertEqual(
            self.node_toyama.get_city_local_authority_code(),
            '162019')


if __name__ == '__main__':
    unittest.main()
