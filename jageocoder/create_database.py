import gzip
import logging
import os

from jageocoder.address import AddressNode, AddressTree

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    build_from_file = False
    build_trie = True

    if build_from_file:
        if os.path.exists('./db/all_latlon.db'):
            os.remove('./db/all_latlon.db')

        tree = AddressTree(dsn="sqlite:///db/all_latlon.db",
                           trie="db/all_latlon.trie", debug=False)
        tree.create_db()

        with gzip.open('data/dams.txt.gz', mode='rt',
                       encoding='EUC_JP', errors='backslashreplace') as f:
            tree.read_stream(f, grouping_level=4)

        tree.create_tree_index()
            
    else:
        tree = AddressTree(dsn="sqlite:///db/all_latlon.db", trie="db/all_latlon.trie", debug=False)
        tree.create_tree_index()

    if build_trie:
        tree.create_trie_index()
        
    
    query = '青森県つがる市柏稲盛幾世172-'
    print(tree.search_by_trie(query))

    query = ['青森県','つがる市','柏稲盛','幾世','１７２番地']
    node = tree.search(query)
    print("{} => {}".format(query, repr(node)))
    
    query = ['青森県','つがる市','柏稲盛','字幾世','172番地']
    node = tree.search(query)
    print("{} => {}".format(query, repr(node)))
