import logging
from typing import Any, Dict
import unittest

import jageocoder

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


class TestDocumentSamples(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        jageocoder.init()

    def test_index_search(self):
        """
        Sample code in `docs/source/index.rst`

        >>> jageocoder.search('新宿区西新宿2-8-1')
        """
        result = jageocoder.search('新宿区西新宿2-8-1')
        self.assertTrue(isinstance(result, dict))
        r: Dict[str, Any] = result  # type: ignore
        self.assertEqual(r["matched"], '新宿区西新宿2-8-')
        self.assertIn("candidates", r)
        self.assertEqual(len(r["candidates"]), 1)
        c = r["candidates"][0]
        self.assertTrue(isinstance(c["id"], int))
        self.assertEqual(c["name"], "8番")
        self.assertTrue(round(c["x"], 3) == 139.692)
        self.assertTrue(round(c["y"], 3) == 35.690)
        self.assertEqual(c["level"], 7)
        self.assertTrue(isinstance(c["priority"], int))
        self.assertTrue(isinstance(c["note"], str))
        self.assertEqual(
            c["fullname"],
            ['東京都', '新宿区', '西新宿', '二丁目', '8番'])

    def test_index_reverse(self):
        """
        Sample code in `docs/source/index.rst`

        >>> jageocoder.reverse(139.691772, 35.689628, level=7)[0]
        """
        result = jageocoder.reverse(139.691772, 35.689628, level=7)
        self.assertTrue(isinstance(result, list))
        self.assertTrue(len(result) > 0)
        r = result[0]
        self.assertTrue(r["dist"] < 1.0)
        self.assertIn("candidate", r)
        self.assertTrue(isinstance(r["candidate"], dict))
        c = r["candidate"]
        self.assertTrue(isinstance(c["id"], int))
        self.assertEqual(c["name"], "8番")
        self.assertTrue(round(c["x"], 3) == 139.692)
        self.assertTrue(round(c["y"], 3) == 35.690)
        self.assertEqual(c["level"], 7)
        self.assertTrue(isinstance(c["priority"], int))
        self.assertTrue(isinstance(c["note"], str))
        self.assertEqual(
            c["fullname"],
            ['東京都', '新宿区', '西新宿', '二丁目', '8番'])


if __name__ == '__main__':
    unittest.main()
