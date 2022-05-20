import logging
import os
import shutil
import tempfile
import unittest

import jageocoder
from jageocoder.tree import AddressTree

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


class TestCreateDBMethods(unittest.TestCase):

    basedir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../'))
    textpath = os.path.join(basedir, 'data/test.txt')
    zippath = os.path.join(basedir, 'data/test_jusho.zip')
    tree = None

    def test_create(self):
        with tempfile.TemporaryDirectory('test_create_') as base_dir:
            db_dir = os.path.join(base_dir, 'jageocoder')
            os.mkdir(db_dir, mode=0o755)
            self.tree = AddressTree(db_dir=db_dir, mode='w')

            with open(self.textpath, mode='r', encoding='utf-8') as f:
                self.tree.read_stream(f)

            self.tree.create_tree_index()

            node = self.tree.search_by_tree(
                ['青森県', '三戸郡', '階上町', '大字道仏', '二ノ窪', '１番地'])
            self.assertEqual(node.name, '１番地')

            if os.path.exists(self.tree.trie_path):
                os.remove(self.tree.trie_path)

            self.tree.create_trie_index()

            result = self.tree.searchNode('階上町大字道仏二の窪１番地')
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0][1], '階上町大字道仏二の窪１番地')

            self.tree.close()
            del self.tree

            shutil.make_archive(
                str(self.zippath)[:-4],
                format='zip',
                root_dir=db_dir,
                logger=logger)

    def test_install(self):
        with tempfile.TemporaryDirectory('test_create_') as base_dir:
            db_dir = os.path.join(base_dir, 'jageocoder')
            jageocoder.install_dictionary(self.zippath, db_dir=db_dir)
            result = jageocoder.get_module_tree().searchNode('階上町大字道仏二の窪１番地')
            self.assertEqual(len(result), 1)
            self.assertEqual(result[0][1], '階上町大字道仏二の窪１番地')
            jageocoder.free()

            jageocoder.uninstall_dictionary(db_dir=db_dir)
            self.assertFalse(os.path.exists(db_dir))


if __name__ == '__main__':
    logging.basicConfig(level=logging.DEBUG)
    unittest.main()
