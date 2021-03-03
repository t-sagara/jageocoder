import bz2
import logging
import os

from jageocoder.address import AddressNode, AddressTree

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    build_from_file = True
    build_trie = True

    basedir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../'))

    dbpath = os.path.join(basedir, 'db/isj.db')
    triepath = os.path.join(basedir, 'db/isj.trie')
    datapath = os.path.join(basedir, 'data/isj.txt.bz2')

    if build_from_file:
        if os.path.exists(dbpath):
            os.remove(dbpath)

        tree = AddressTree(dsn="sqlite:///" + dbpath,
                           trie_path=triepath, debug=False)
        tree.create_db()

        with bz2.open(datapath, mode='rt', encoding='utf-8') as f:
            tree.read_stream(f, do_update=False)

        tree.create_tree_index()

    else:
        tree = AddressTree(dsn="sqlite:///" + dbpath,
                           trie_path=triepath, debug=False)
        tree.create_tree_index()

    if build_trie:
        tree.create_trie_index()
