import gzip
import logging
import os

from jageocoder.address import AddressNode, AddressTree

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    build_from_file = False
    build_trie = True

    dbpath = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../db/all_latlon.db'))
    triepath = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../db/all_latlon.trie'))
    datapath = os.path.abspath(os.path.join(
        os.path.dirname(__file__), '../data/all_latlon.utf8.gz'))
    
    if build_from_file:
        if os.path.exists(dbpath):
            os.remove(dbpath)

        tree = AddressTree(dsn="sqlite:///" + dbpath,
                           trie=triepath, debug=False)
        tree.create_db()

        #with gzip.open('data/dams.txt.gz', mode='rt',
        #               encoding='EUC_JP', errors='backslashreplace') as f:
        with gzip.open(datapath, mode='rt', encoding='utf-8') as f:
            tree.read_stream(f, grouping_level=4)

        tree.create_tree_index()
            
    else:
        tree = AddressTree(dsn="sqlite:///" + dbpath,
                           trie=triepath, debug=False)
        tree.create_tree_index()

    if build_trie:
        tree.create_trie_index()
        
    
    query = '青森県つがる市柏稲盛幾世172-'
    print(tree.search_by_trie(query))

    query = ['青森県','つがる市','柏稲盛','幾世','１７２番地']
    node = tree.search_by_tree(query)
    print("{} => {}".format(query, repr(node)))
    
    query = ['青森県','つがる市','柏稲盛','字幾世','172番地']
    node = tree.search_by_tree(query)
    print("{} => {}".format(query, repr(node)))
