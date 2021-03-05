import logging
import os

from jageocoder.address import AddressNode, AddressTree

if __name__ == '__main__':

    logging.basicConfig(level=logging.INFO)

    build_from_file = True
    build_trie = True

    basedir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../'))

    dbpath = os.path.join(basedir, 'db/full.db')
    triepath = os.path.join(basedir, 'db/full.trie')
    datapath = os.path.join(basedir, 'data/full.utf8.bz2')

    if build_from_file:
        if os.path.exists(dbpath):
            os.remove(dbpath)

        tree = AddressTree(dsn="sqlite:///" + dbpath,
                           trie_path=triepath, debug=False)
        tree.create_db()
        tree.create_tree_index()

        for i in range(0, 48): # 0,48
            filepath = os.path.join(basedir, 'converter/mlit-isj/',
                                    "{:02d}.txt".format(i))
            logging.info("Loading {}".format(filepath))
            with open(filepath, mode='r', encoding='utf-8') as f:
                tree.read_stream(f, do_update=False)

                
        # tree.create_tree_index()

    else:
        tree = AddressTree(dsn="sqlite:///" + dbpath,
                           trie_path=triepath, debug=False)
        tree.create_tree_index()

    if build_trie:
        tree.create_trie_index()
