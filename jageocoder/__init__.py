import logging
import os
import tempfile
from typing import Optional, NoReturn, Union
import urllib.request
from urllib.error import URLError
import zipfile

from jageocoder.tree import AddressTree, get_db_dir
from jageocoder.node import AddressNode
from jageocoder.itaiji import converter as itaiji_converter
from jageocoder.address import AddressLevel

__all__ = [
    AddressLevel,  # Definition of levels of address elements
    AddressNode,   # 'node' table definition
    AddressTree,   # Tree and TRIE management class of address nodes
    itaiji_converter,  # The singleton converter object
]

_tree = None

logger = logging.getLogger(__name__)


class JageocoderError(RuntimeError):
    """
    Custom exception classes sent out by jageocoder module.
    """
    pass


def init(dsn: Optional[str] = None,
         trie_path: Optional[str] = None,
         db_dir: Optional[str] = None,
         mode: Optional[str] = 'r',
         debug: Optional[bool] = False) -> NoReturn:
    """
    Initialize the module-level AddressTree object `jageocoder.tree`
    ready for use.

    Parameters
    ----------
    dsn: str, optional
        Data Source Name of the database.
    trie_path: str, optional
        File path to save the TRIE index.
    db_dir: str, optional
        The database directory.
        If dsn and trie_path are omitted and db_dir is set,
        'address.db' and 'address.trie' under this directory will be used.
    mode: str, optional(default='r')
        Specifies the mode for opening the database.
        - In the case of 'a', if the database already exists, it will be used.
          If it does not exist, create a new one.
        - In the case of 'w', if the database already exists, delete it first.
          Then create a new one.
        - In the case of 'r', if the database already exists, it will be used.
          Otherwise raise a JageocoderError exception.
    debug: bool, Optional(default=False)
        Debugging flag.
    """
    global _tree

    if _tree:
        _tree.close()

    _tree = AddressTree(dsn=dsn, trie_path=trie_path, db_dir=db_dir,
                        mode=mode, debug=debug)


def is_initialized() -> bool:
    """
    Checks if the module has been initialized with `init()`.

    Return
    ------
    bool
        True if the module is initialized, otherwise False.
    """
    if get_module_tree():
        return True

    return False


def get_module_tree() -> Union[AddressTree, None]:
    """
    Get the module-level AddressTree singleton object.

    Return
    ------
    AddressTree
        The singleton object.
    """
    global _tree
    return _tree


def install_dictionary(path_or_url: Optional[str] = 'jusho.zip',
                       db_dir: Optional[str] = None) -> NoReturn:
    """
    Install address-dictionary from the specified path or url.

    Parameters
    ----------
    path_or_url: str, optional
        The file path or url where the zipped address-dictionary file
        is available.
        If omitted, try to open 'jusho.zip' in the current directory.

    db_dir: str, optional
        The directory where the database files will be installed.
        If omitted, it will be determined by `get_db_dir()`.
    """
    # Set default value
    if db_dir is None:
        db_dir = get_db_dir(mode='w')

    # Open a local file
    tmppath = None
    if os.path.exists(path_or_url):
        path = path_or_url
    else:
        try:
            # Try to download a file
            fp, path = tempfile.mkstemp()
            os.close(fp)
            logger.debug(
                'Downloading zipped dictionary from {}'.format(path_or_url))
            urllib.request.urlretrieve(path_or_url, path)
            logger.debug('.. download complete.')
            tmppath = path
        except (URLError, ValueError,):
            raise JageocoderError("Can't open file {}".format(path_or_url))

    # Unzip the file
    with zipfile.ZipFile(path) as zipf:
        logger.debug('Extracting address.db to {}'.format(db_dir))
        zipf.extract(member='address.db', path=db_dir)

    if tmppath:
        os.remove(tmppath)

    # Create trie-index
    init(db_dir=db_dir, mode='a')
    global _tree
    logger.debug('Creating TRIE index {}'.format(_tree.trie_path))
    _tree.create_trie_index()
    logger.debug('Dictionary installation complete.')


def search(query: str) -> dict:
    """
    Search node from the tree by the query.

    Parameters
    ---------
    query: str
        An address notation to be searched.

    Return
    ------
    A dict containing the following elements.

    matched: str
        The matching substring.
    candidates: list of dict
        List of dict representation of nodes with
        the longest match to the query string.
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    results = _tree.searchNode(query, True)

    if len(results) == 0:
        return {'matched': '', 'candidates': []}

    return {
        'matched': results[0][1],
        'candidates': [x[0].as_dict() for x in results],
    }


def searchNode(query: str, best_only: Optional[bool] = True):
    """
    Searches for address nodes corresponding to an address notation
    and returns the matching substring and a list of nodes.

    Parameters
    ----------
    query : str
        An address notation to be searched.
    best_only: bool, optional
        If set to False, Returns all candidates whose prefix matches.

    Return
    ------
    list
        A list of AddressNode and matched substring pairs.

    Note
    ----
    The `search_by_trie` function returns the standardized string
    as the match string. In contrast, the `searchNode` function returns
    the de-starndized string.

    Example
    -------
    >>> import jageocoder
    >>> jageocoder.init()
    >>> jageocoder.searchNode('多摩市落合1-15-2')
    [[[11460207:東京都(139.69178,35.68963)1(lasdec:130001/jisx0401:13)]>[12063502:多摩市(139.446366,35.636959)3(jisx0402:13224)]>[12065383:落合(139.427097,35.624877)5(None)]>[12065384:一丁目(139.427097,35.624877)6(None)]>[12065390:15番地(139.428969,35.625779)7(None)], '多摩市落合1-15-']]
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    return _tree.searchNode(query, best_only)


def create_trie_index() -> NoReturn:
    """
    Create the TRIE index from the database file.

    This function is a shortcut for AddressTree.create_trie_index().
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    _tree.create_trie_index()
