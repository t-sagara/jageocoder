import logging
import os
import tempfile
from typing import Optional, NoReturn, Union
import urllib.request
from urllib.error import URLError
import zipfile

import jageocoder
from jageocoder.exceptions import JageocoderError
from jageocoder.tree import AddressTree, get_db_dir

_tree = None  # The default AddressTree
logger = logging.getLogger(__name__)


def init(dsn: Optional[str] = None,
         trie_path: Optional[os.PathLike] = None,
         db_dir: Optional[os.PathLike] = None,
         mode: Optional[str] = 'r',
         debug: Optional[bool] = False) -> NoReturn:
    """
    Initialize the module-level AddressTree object `jageocoder.tree`
    ready for use.

    Parameters
    ----------
    dsn: str, optional
        Data Source Name of the database.
    trie_path: os.PathLike, optional
        File path to save the TRIE index.
    db_dir: os.PathLike, optional
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


def download_dictionary(url: str) -> NoReturn:
    """
    Download address-dictionary from the specified url into
    the current directory.

    Parameters
    ----------
    url: str
        The URL where the zipped address-dictionary file is available.
    """
    path = os.path.join(os.getcwd(),
                        os.path.basename(url))

    try:
        # Try to download the file
        logger.info((
            'Downloading zipped dictionary file from {url}'
            ' to {path}').format(url=url, path=path))
        urllib.request.urlretrieve(url, path)
        logger.info('.. download complete.')
    except (URLError, ValueError,):
        raise JageocoderError(
            "The dictionary file could not be downloaded"
            + " from the URL {}".format(url))


def install_dictionary(
        path_or_url: os.PathLike,
        db_dir: Optional[os.PathLike] = None) -> NoReturn:
    """
    Install address-dictionary from the specified path or url.

    Parameters
    ----------
    path_or_url: os.PathLike
        The file path or url where the zipped address-dictionary file
        is available.

    db_dir: os.PathLike, optional
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
            logger.info(
                'Downloading zipped dictionary from {}'.format(path_or_url))
            urllib.request.urlretrieve(path_or_url, path)
            logger.info('.. download complete.')
            tmppath = path
        except (URLError, ValueError,):
            raise JageocoderError("Can't open file {}".format(path_or_url))

    # Unzip the file
    with zipfile.ZipFile(path) as zipf:
        logger.info('Extracting {} to {}'.format(path, db_dir))
        zipf.extract(member='address.db', path=db_dir)
        try:
            zipf.extract(member='README.txt', path=db_dir)
            logger.info(
                'Please check {} for terms and conditions of use.'.format(
                    os.path.join(db_dir, 'README.txt')))
        except KeyError:
            pass

    if tmppath:
        os.remove(tmppath)

    # Create trie-index
    init(db_dir=db_dir, mode='a')
    global _tree
    if not _tree.is_version_compatible():
        logger.warning(('Updating the database file since'
                        ' it is not compatible with the package.'))
        _tree.update_name_index()

    logger.info('Creating TRIE index at {}'.format(_tree.trie_path))
    _tree.create_trie_index()
    logger.info('Installation completed.')


def uninstall_dictionary(db_dir: Optional[os.PathLike] = None) -> NoReturn:
    """
    Uninstall address-dictionary.

    Parameters
    ----------
    db_dir: os.PathLike, optional
        The directory where the database files has been installed.
        If omitted, it will be determined by `get_db_dir()`.
    """
    # Set default value
    if db_dir is None:
        db_dir = get_db_dir(mode='w')

    # Remove the directory
    logger.info('Removing directory {}'.format(db_dir))
    import shutil
    shutil.rmtree(db_dir)
    logger.info('Dictionary has been uninstalled.')


def upgrade_dictionary(db_dir: Optional[os.PathLike] = None) -> NoReturn:
    """
    Upgrade address-dictionary.

    Parameters
    ----------
    db_dir: os.PathLike, optional
        The directory where the database files has been installed.
        If omitted, it will be determined by `get_db_dir()`.
    """
    # Set default value
    if db_dir is None:
        db_dir = get_db_dir(mode='a')

    # Upgrade the name and trie index
    init(db_dir=db_dir, mode='a')
    global _tree
    logger.info('Updating name index')
    _tree.update_name_index()
    logger.info('Updating TRIE index {}'.format(_tree.trie_path))
    _tree.create_trie_index()
    logger.info('The dictionary is successfully upgraded.')


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


def version():
    return jageocoder.__version__


def dictionary_version():
    return jageocoder.__dictionary_version__
