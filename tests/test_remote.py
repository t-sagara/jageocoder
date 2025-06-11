import os
import unittest

import jageocoder
from jageocoder.exceptions import RemoteTreeException
from jageocoder.node import AddressNode
from jageocoder.result import Result


class TestRemoteMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        url = os.environ.get("JAGEOCODER_SERVER_URL")
        if url is None:
            # url = "https://jageocoder.info-proto.com/jsonrpc"
            url = "http://jageocoder:5000/jsonrpc"

        jageocoder.init(url=url)
        cls.tree = jageocoder.get_module_tree()

    def _get_first_node(self, query: str) -> AddressNode:
        results = self.tree.searchNode(query)
        return results[0].get_node()

    def test_get_dictionary_version(self):
        version = jageocoder.installed_dictionary_version(
            url=jageocoder.get_module_tree().url,
        )
        self.assertTrue(isinstance(version, str))

    def test_search(self):
        jageocoder.set_search_config(best_only=True)
        result = jageocoder.search(query="新宿区西新宿２丁目８−１")
        self.assertTrue(len(result["matched"]) > 10)
        self.assertTrue(isinstance(result["candidates"], list))
        node = result["candidates"][0]
        self.assertTrue(isinstance(node, dict))

    def test_search_set_config(self):
        jageocoder.set_search_config(target_area='14152')
        result = jageocoder.search(query="中央区中央1-1-1")
        self.assertTrue(len(result["matched"]) == 10)
        self.assertTrue(len(result["candidates"]) == 1)

        jageocoder.set_search_config(target_area=['13', '14152'])
        result = jageocoder.search(query="中央区中央1-1-1")
        self.assertTrue(len(result["matched"]) == 10)
        self.assertTrue(len(result["candidates"]) == 1)

        with self.assertRaises(RuntimeError):
            jageocoder.set_search_config(target_area=['東京都', '相模原市'])

    def test_search_node(self):
        results = jageocoder.searchNode(query="新宿区西新宿２丁目８−１")
        self.assertEqual(type(results[0]), Result)
        node = results[0].get_node()
        parent = node.get_parent()
        self.assertIsNotNone(parent)
        self.assertTrue(parent.level < node.level)
        self.assertEqual(node.get_city_jiscode(), "13104")

    def test_reverse(self):
        results = jageocoder.reverse(
            y=35.689472, x=139.69175, level=7, as_dict=False
        )
        nearest_node = results[0]["candidate"]
        self.assertTrue(isinstance(nearest_node, AddressNode))
        self.assertEqual(nearest_node.dataset["title"], "街区レベル位置参照情報")

    def test_search_machiaza(self):
        results = jageocoder.search_by_machiaza_id(id='1310410023002')
        self.assertEqual(len(results), 1)
        node = results[0]
        self.assertTrue(isinstance(node, AddressNode))
        self.assertTrue(node.name == '二丁目' and node.parent.name == '西新宿')

        results = jageocoder.search_by_machiaza_id(id='131040023002')
        self.assertEqual(len(results), 1)
        node = results[0]
        self.assertTrue(isinstance(node, AddressNode))
        self.assertTrue(node.name == '二丁目' and node.parent.name == '西新宿')

    def test_search_postcode(self):
        results = jageocoder.search_by_postcode(code='1600023')
        self.assertTrue(len(results) >= 8)
        node = results[0]
        self.assertTrue(isinstance(node, AddressNode))
        self.assertTrue(node.name[-2:] == '丁目' and node.parent.name == '西新宿')

    def test_search_citycode(self):
        results = jageocoder.search_by_citycode(code='131041')
        self.assertTrue(len(results) >= 1)
        node = results[0]
        self.assertTrue(isinstance(node, AddressNode))
        self.assertEqual(node.name, '新宿区')

        results = jageocoder.search_by_citycode(code='13104')
        self.assertTrue(len(results) >= 1)
        node = results[0]
        self.assertTrue(isinstance(node, AddressNode))
        self.assertEqual(node.name, '新宿区')

    def test_search_prefcode(self):
        results = jageocoder.search_by_prefcode(code='130001')
        self.assertTrue(len(results) >= 1)
        node = results[0]
        self.assertTrue(isinstance(node, AddressNode))
        self.assertTrue(node.name in ('東京', '東京都'))

        results = jageocoder.search_by_prefcode(code='13')
        self.assertTrue(len(results) >= 1)
        node = results[0]
        self.assertTrue(isinstance(node, AddressNode))
        self.assertTrue(node.name in ('東京', '東京都'))

    def test_get_pref_name(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_pref_name(), '東京都')

    def test_get_pref_jiscode(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_pref_jiscode(), '13')

    def test_get_pref_local_authority_code(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_pref_local_authority_code(), '130001')

    def test_get_city_name(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_city_name(), '新宿区')

    def test_get_city_jiscode(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_city_jiscode(), '13104')

    def test_get_city_local_authority_code(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_city_local_authority_code(), '131041')

    def test_get_aza_id(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_aza_id(), '0023002')

    def test_get_machiaza_id(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_machiaza_id(), '0023002')

    def test_get_aza_code(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_aza_code(), '131040023002')

    def test_get_aza_names(self):
        with self.assertRaises(RemoteTreeException):
            self._get_first_node("新宿区西新宿2-8-1").get_aza_names()

    def test_get_postcode(self):
        self.assertEqual(self._get_first_node(
            "新宿区西新宿2-8-1").get_postcode(), '1600023')


if __name__ == '__main__':
    unittest.main()
