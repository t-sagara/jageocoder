import logging
import time

from address import AddressNode, AddressTree

if __name__ == '__main__':

    logging.basicConfig(level=logging.DEBUG)

    time0 = time.time()

    tree = AddressTree(dsn="sqlite:///data/02.db", trie="data/02.trie", debug=False)  # True
    query = '柏上古川房田139-'
    #query = '青森県つがる市柏上古川房田139-'
    print("query='{}'".format(query))
    print(tree.search_by_trie(query))
    print('tree.search_by_trie(<QUERY>)')
    exit(0)

    root = tree.get_root()

    time1 = time.time()
    logging.info("Setup: {}".format(time1 - time0))

    query = ['青森県', 'つがる市', '柏稲盛', '幾世', '１７２番地']
    node = tree.search(query)

    time2 = time.time()
    logging.info("Search 1: {}".format(time2 - time1))

    print("{} => {}".format(query, repr(node)))

    time3 = time.time()
    logging.info("Print 1: {}".format(time3 - time2))

    query = ['青森県', 'つがる市', '柏稲盛', '字幾世', '172番地']
    node = tree.search(query)
    
    time4 = time.time()
    logging.info("Search 1: {}".format(time4 - time3))

    print("{} => {}".format(query, repr(node)))

    time5 = time.time()
    logging.info("Print 1: {}".format(time5 - time4))
