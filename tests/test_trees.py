import logging
import os
from pathlib import Path
import shutil
import unittest

from jageocoder.exceptions import AddressTreeException
from jageocoder.tree import AddressTree
from jageocoder.local import LocalTree
from jageocoder.remote import RemoteTree

logger = logging.getLogger(__name__)
# logging.basicConfig(level=logging.INFO)


class TestTreeMethods(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.db_dir = os.environ.get("JAGEOCODER_DB2_DIR")
        cls.url = os.environ.get(
            "JAGEOCODER_SERVER_URL",
            "https://jageocoder.info-proto.com/jsonrpc")
        cls.testdb_dir = os.path.join(os.path.dirname(__file__), "testdb")
        if os.environ.get("JAGEOCODER_DB2_DIR"):
            del os.environ["JAGEOCODER_DB2_DIR"]

        if os.environ.get("JAGEOCODER_SERVER_URL"):
            del os.environ["JAGEOCODER_SERVER_URL"]

    def test_create_local_tree_for_read(self):
        if self.db_dir is None:
            self.skipTest("Skip create local tree")

        db_dir = Path(self.db_dir)
        tree = AddressTree(db_dir=db_dir, mode="r")
        self.assertTrue(isinstance(tree, LocalTree))

    def test_create_local_tree_for_read_with_envvar(self):
        if self.db_dir is None:
            self.skipTest("Skip create local tree")

        os.environ["JAGEOCODER_DB2_DIR"] = self.db_dir
        tree = AddressTree(mode="r")
        self.assertTrue(isinstance(tree, LocalTree))
        if isinstance(tree, LocalTree):
            self.assertEqual(tree.db_dir, Path(
                os.environ["JAGEOCODER_DB2_DIR"]))
        del os.environ["JAGEOCODER_DB2_DIR"]

    def test_create_local_tree_for_write(self):
        if os.path.exists(self.testdb_dir):
            shutil.rmtree(self.testdb_dir)

        testdb_dir = Path(self.testdb_dir)
        tree = AddressTree(db_dir=testdb_dir, mode="w")
        self.assertTrue(isinstance(tree, LocalTree))

        if testdb_dir.exists():
            shutil.rmtree(self.testdb_dir)

    def test_create_local_tree_with_nodb(self):
        if os.path.exists(self.testdb_dir):
            shutil.rmtree(self.testdb_dir)

        testdb_dir = Path(self.testdb_dir)
        with self.assertRaises(AddressTreeException):
            _ = AddressTree(db_dir=testdb_dir, mode="r")

    def test_create_remote_tree(self):
        tree = AddressTree(url=self.url)
        self.assertTrue(isinstance(tree, RemoteTree))

    def test_create_remote_tree_with_envvar(self):
        os.environ["JAGEOCODER_SERVER_URL"] = self.url
        tree = AddressTree()
        self.assertTrue(isinstance(tree, RemoteTree))
        if isinstance(tree, RemoteTree):
            self.assertEqual(tree.url, os.environ["JAGEOCODER_SERVER_URL"])
        del os.environ["JAGEOCODER_SERVER_URL"]

    def test_create_address_tree(self):
        # Escape and remove environ values
        envs = ("JAGEOCODER_DB2_DIR", "JAGEOCODER_SERVER_URL")
        cur_envs = {}
        for e in envs:
            v = os.environ.get(e)
            if v is not None:
                cur_envs[e] = os.environ.get(e)
                del os.environ[e]

        with self.assertRaises(AddressTreeException):
            _ = AddressTree(debug=True)

        # Restore environ values
        for e in envs:
            v = cur_envs.get(e)
            if v is not None:
                os.environ[e] = v
