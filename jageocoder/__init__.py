import os

from .address import AddressTree

tree = None

def init(dsn, trie):
    """
    Initialize AddressTree.

    Parameters
    ----------
    dsn : str
        RFC-1738 based database-url, so called "data source name".
    trie_path : str
        File path to save the TRIE index.

    Return
    ------
    The AddressTree object.
    """
    global tree
    
    tree = AddressTree(dsn, trie)

def search(query):
    """
    Search node from the tree by the query.

    Parameter
    ---------
    query : str
        The address string to be retrieved.
   
    Return
    ------
    
    """
    result = tree.search(query)
    result['candidates'] = [x.as_dict() for x in result['candidates']]

    return result
