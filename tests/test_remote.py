import os
import unittest

import jageocoder


class TestRemoteMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        url = os.environ.get("JAGEOCODER_SERVER_URL")
        if url is None:
            url = "https://jageocoder.info-proto.com/jsonrpc"
            # url = "http://jageocoder:5000/jsonrpc"

        jageocoder.init(url=url)

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

    def test_search_node(self):
        results = jageocoder.searchNode(query="新宿区西新宿２丁目８−１")
        self.assertEqual(type(results[0]), jageocoder.result.Result)
        node = results[0].node
        parent = node.parent
        self.assertTrue(parent.level < node.level)
        self.assertEqual(node.get_city_jiscode(), "13104")

    def test_reverse(self):
        results = jageocoder.reverse(
            y=35.689472, x=139.69175, level=7, as_dict=False
        )
        nearest_node = results[0]["candidate"]
        self.assertTrue(isinstance(nearest_node, jageocoder.node.AddressNode))
        self.assertEqual(nearest_node.dataset["title"], "街区レベル位置参照情報")


if __name__ == '__main__':
    unittest.main()
