import logging
import os

from jageocoder.address import AddressTree

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    basedir = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../'))

    dbpath = os.path.join(basedir, 'db/isj.db')
    triepath = os.path.join(basedir, 'db/isj.trie')
    datapath = os.path.join(basedir, 'data/offices.txt')

    tree = AddressTree(dsn="sqlite:///" + dbpath,
                       trie_path=triepath, debug=False)
    with open(datapath, mode='r', encoding='utf-8') as f:
        tree.read_stream(f, do_update=True)


    
