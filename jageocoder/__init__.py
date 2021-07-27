import logging
import os
import tempfile
from typing import Optional, NoReturn, Union
import urllib.request
from urllib.error import URLError
import zipfile

from jageocoder.tree import AddressTree, get_db_dir
tree = None

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
    global tree

    if tree:
        tree.close()

    tree = AddressTree(dsn=dsn, trie_path=trie_path, db_dir=db_dir,
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
    global tree
    return tree


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
    tree = get_module_tree()
    logger.debug('Creating TRIE index {}'.format(tree.trie_path))
    tree.create_trie_index()

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
    if tree is None:
        raise JageocoderError("Not initialized. Call 'init()' first.")

    results = tree.search(query)

    if len(results) == 0:
        return {'matched': '', 'candidates': []}

    return {
        'matched': results[0][1],
        'candidates': [x[0].as_dict() for x in results],
    }


def create_trie_index() -> NoReturn:
    """
    Create the TRIE index from the database file.

    This function is a shortcut for AddressTree.create_trie_index().
    """
    if tree is None:
        raise JageocoderError("Not initialized. Call 'init()' first.")

    tree.create_trie_index()
