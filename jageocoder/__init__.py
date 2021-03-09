import os

from .address import AddressTree

tree = None


class JageocoderError(RuntimeError):
    pass


def init(dsn, trie_path):
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

    tree = AddressTree(dsn, trie_path)


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
    if tree is None:
        raise JageocoderError("Not initialized. Call 'init()' first.")

    results = tree.search(query)

    if len(results) == 0:
        return {'matched':'', 'candidates':[]}

    return {
        'matched': results[0][1],
        'candidates': [x[0].as_dict() for x in results],
    }

def create_trie_index():
    """
    Create the TRIE index from the database file.

    This function is a shortcut for AddressTree.create_trie_index().

    Parameteres
    -----------
    No parameter required.

    Return
    ------
    No value.
    """
    if tree is None:
        raise JageocoderError("Not initialized. Call 'init()' first.")

    results = tree.create_trie_index()
