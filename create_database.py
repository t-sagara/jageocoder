import logging
import os

from address import AddressNode, AddressTree

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    build_from_file = True
    build_trie = True

    if build_from_file:
        if os.path.exists('./data/02.db'):
            os.remove('./data/02.db')

        tree = AddressTree(dsn="sqlite:///data/02.db", trie="data/02.trie", debug=False)
        tree.create_db()
    
        tree.read_file('data/02000_latlon.utf8')
        # tree.read_file('02000_latlon_debug.utf8')
        
        tree.save()
        
    else:
        tree = AddressTree(dsn="sqlite:///data/02.db", trie="data/02.trie", debug=False)

    if build_from_file and build_trie:
        tree.create_trie_index()
        

    query = '青森県つがる市柏稲盛幾世172-'
    print(tree.search_by_trie(query))

    query = ['青森県','つがる市','柏稲盛','幾世','１７２番地']
    node = tree.search(query)
    print("{} => {}".format(query, repr(node)))
    
    query = ['青森県','つがる市','柏稲盛','字幾世','172番地']
    node = tree.search(query)
    print("{} => {}".format(query, repr(node)))

    
