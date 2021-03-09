import logging
import os
import unittest

from jageocoder.address import AddressNode, AddressTree

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)

class TestCreateDBMethods(unittest.TestCase):

    def setUp(self):
        basedir = os.path.abspath(os.path.join(
            os.path.dirname(__file__), '../'))
        logging.basicConfig(level=logging.INFO)
        self.textpath = os.path.join(basedir, 'data/test.txt')
        self.dbpath = os.path.join(basedir, 'db/test.db')
        self.triepath = os.path.join(basedir, 'db/test.trie')
        self.tree = AddressTree(dsn="sqlite:///" + self.dbpath,
                                trie_path=self.triepath, debug=False)

    def test_create(self):
        if os.path.exists(self.dbpath):
            os.remove(self.dbpath)

        self.tree.create_db()

        with open(self.textpath, mode='r', encoding='utf-8') as f:
            self.tree.read_stream(f)

        self.tree.create_tree_index()

        node = self.tree.search_by_tree(
            ['青森県', '三戸郡', '階上町', '大字道仏', '二ノ窪', '１番地'])
        self.assertEqual(node.name, '１番地')

        if os.path.exists(self.triepath):
            os.remove(self.triepath)

        self.tree.create_trie_index()

        result = self.tree.search('階上町大字道仏二の窪１番地')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], '階上町大字道仏二の窪１番地')
