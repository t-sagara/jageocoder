import logging
import time

from address import AddressNode, AddressTree

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    time0 = time.time()

    tree = AddressTree(dsn="sqlite:///db/all_latlon.db", trie="db/all_latlon.trie", debug=False)  # True
    query = '青森県つがる市柏稲盛幾世172-'
    print("query='{}'".format(query))
    print(tree.search_by_trie(query))
    
    print('tree.search_by_trie(<QUERY>)')
    import pdb; pdb.set_trace()
