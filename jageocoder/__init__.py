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

    Parameters
    ---------
    query : str
        An address notation to be searched.

    Return
    ------
    A dict containing the following elements.

    matched : str
        The matching substring.
    candidates : list of dict
        List of dict representation of nodes with
        the longest match to the query string.
    """
    result = tree.search(query)
    result['candidates'] = [x.as_dict() for x in result['candidates']]

    return result
