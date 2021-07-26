import logging
import os
import shutil
import unittest

from jageocoder.tree import AddressTree

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


class TestCreateDBMethods(unittest.TestCase):

    basedir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../'))
    textpath = os.path.join(basedir, 'data/test.txt')
    tree = None

    @classmethod
    def setUpClass(cls):
        cls.db_dir = 'test_createdb'
        if os.path.exists(cls.db_dir):
            shutil.rmtree(cls.db_dir)

        os.makedirs(cls.db_dir, mode=0o777)

    def test_create(self):
        self.tree = AddressTree(db_dir=self.db_dir, mode='w')
        self.tree.create_db()

        with open(self.textpath, mode='r', encoding='utf-8') as f:
            self.tree.read_stream(f)

        self.tree.create_tree_index()

        node = self.tree.search_by_tree(
            ['青森県', '三戸郡', '階上町', '大字道仏', '二ノ窪', '１番地'])
        self.assertEqual(node.name, '１番地')

        if os.path.exists(self.tree.trie_path):
            os.remove(self.tree.trie_path)

        self.tree.create_trie_index()

        result = self.tree.search('階上町大字道仏二の窪１番地')
        self.assertEqual(len(result), 1)
        self.assertEqual(result[0][1], '階上町大字道仏二の窪１番地')


if __name__ == '__main__':
    unittest.main()
