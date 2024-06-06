import datetime
import logging
import os
import shutil
from typing import Optional, Union, List
import urllib.request
from urllib.error import URLError

import jageocoder
from jageocoder.exceptions import JageocoderError
from jageocoder.tree import AddressTree, get_db_dir
from jageocoder.remote import RemoteTree
from jageocoder.result import Result

_tree = None  # The default AddressTree
logger = logging.getLogger(__name__)


def init(db_dir: Optional[os.PathLike] = None,
         mode: Optional[str] = 'r',
         debug: Optional[bool] = False,
         url: Optional[str] = None,
         **kwargs) -> None:
    """
    Initialize the module-level AddressTree object `jageocoder.tree`
    ready for use.

    Parameters
    ----------
    db_dir: os.PathLike, optional
        The database directory.
        'address.db' and 'address.trie' are stored in this directory.

    mode: str, optional(default='r')
        Specifies the mode for opening the database.

        - In the case of 'a', if the database already exists, it will be used.
          If it does not exist, create a new one.

        - In the case of 'w', if the database already exists, delete it first.
          Then create a new one.

        - In the case of 'r', if the database already exists, it will be used.
          Otherwise raise a JageocoderError exception.

    debug: bool, optional(default=False)
        Debugging flag.

    url: str, optional
        URL of the Jageocoder server endpoint.

    Notes
    -----
    - If both 'db_dir' and 'url' are specified, 'db_dir' has priority.
    - If both 'db_dir' and 'url' are omitted, it looks for a dictionary
        installed in the jageocoder package dcirectory.
        If not found, a 'JageocoderError' exception is thrown.
    """
    global _tree

    if _tree:
        del _tree

    _url = None
    _db_dir = None

    # Check parameters
    if db_dir is not None:
        _db_dir = db_dir
    elif url is not None and mode == 'r':
        _url = url

    # Check environmental variables
    if _db_dir is None and _url is None:
        if os.environ.get('JAGEOCODER_DB2_DIR'):
            _db_dir = get_db_dir(mode=mode)
        elif os.environ.get('JAGEOCODER_SERVER_URL') and mode == 'r':
            _url = os.environ.get('JAGEOCODER_SERVER_URL')

    # Search local database
    if _db_dir is None and _url is None:
        _db_dir = get_db_dir(mode=mode)

    # Initialize tree object
    if _db_dir:
        _tree = AddressTree(db_dir=_db_dir, mode=mode, debug=debug)
    elif _url:
        _tree = RemoteTree(url=_url, debug=debug)
    else:
        raise JageocoderError(
            "Neither 'db_dir' nor 'url' could be determined.")

    set_search_config(**kwargs)


def free():
    """
    Frees all objects created by 'init()'.
    """
    global _tree
    if _tree:
        _tree.close()

    _tree = None


def set_search_config(**kwargs):
    """
    Set configurable search parameters.

    Note
    ----
    The possible keywords and their meanings are as follows.

    - best_only: bool (default = True)
        If set to False, returns all search result candidates
        whose prefix matches.

    - aza_skip: bool, None (default = False)
        Specifies how to skip aza-names while searching nodes.
        - If None, make the decision automatically
        - If False, do not skip
        - If True, always skip

    - require_coordinates: bool (default = True)
        If set to False, nodes without coordinates are also
        included in the search.

    - target_area: List[str] (Default = [])
        Specify the areas to be searched.
        The area can be specified by the list of name of the node
        (such as prefecture name or city name), or JIS code.

    - auto_redirect: bool (default = True)
        When this option is set and the retrieved node has a
        new address recorded in the "ref" attribute,
        the new address is retrieved automatically.
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    _tree.set_config(**kwargs)


def get_search_config(keys: Union[str, List[str], None] = None) -> dict:
    """
    Get current configurable search parameters.

    Parameters
    ----------
    keys: str, List[str], optional
        If a name of parameter is specified, return its value.
        Otherwise, a dict of specified key and its value pairs
        will be returned.

    Returns
    -------
    Any, or dict.
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    return _tree.get_config(keys)


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


def download_dictionary(url: str) -> None:
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
        path: os.PathLike,
        db_dir: Optional[os.PathLike] = None,
        skip_confirmation: bool = False) -> None:
    """
    Install address-dictionary from the specified path.

    Parameters
    ----------
    path: os.PathLike
        The file path where the zipped address-dictionary file exists.

    db_dir: os.PathLike, optional
        The directory directory where the database files will
        be installed.

        If omitted, use `get_db_dir()` to decide the directory.
    """
    # Set default value
    if db_dir is None:
        db_dir = get_db_dir(mode='w')

    if skip_confirmation is not True and os.path.exists(
            os.path.join(db_dir, 'address_node')):
        # Dictionary had been installed.
        r = input("他の辞書がインストール済みです。上書きしますか？(Y/n) ")
        if r.lower()[0] != 'y':
            return

    if os.path.exists(path):
        path = path
    else:
        raise JageocoderError("Can't open file '{}'".format(path))

    # Unzip the archive
    shutil.rmtree(db_dir)
    shutil.unpack_archive(
        filename=str(path),
        extract_dir=str(db_dir),
    )
    for readme_fname in ("README.txt", "README.md",):
        readme_path = os.path.join(db_dir, readme_fname)
        if os.path.exists(readme_path):
            logger.info(
                "Please read '{}' for terms and conditions of use.".format(
                    readme_path))

    logger.info('Installation completed.')


def uninstall_dictionary(db_dir: Optional[os.PathLike] = None) -> None:
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


def installed_dictionary_version(
    db_dir: Optional[os.PathLike] = None,
    url: Optional[str] = None
) -> str:
    """
    Get the installed dictionary version.

    Parameters
    ----------
    db_dir: os.PathLike, optional
        The directory where the database files has been installed.
        If omitted, it will be determined by `get_db_dir()`.

    url: str, optional
        URL of the Jageocoder server endpoint.

    Returns
    -------
    str
        The version string of the installed dicitionary or the server.
    """
    if db_dir is None:
        if url is not None:
            return RemoteTree(url=url).installed_dictionary_version()

        db_dir = get_db_dir(mode='r')

    metadata_path = os.path.join(db_dir, "metadata.txt")
    if os.path.exists(metadata_path):
        with open(metadata_path, "r") as f:
            version = f.readline().rstrip()

    else:
        readme_path = os.path.join(db_dir, "README.md")
        if os.path.exists(readme_path):
            stats = os.stat(readme_path)
            version = datetime.date.fromtimestamp(stats.st_mtime).strftime(
                '%Y%m%d')
        else:
            version = '(Unknown)'

    return version


def installed_dictionary_readme(
    db_dir: Optional[os.PathLike] = None,
    url: Optional[str] = None
) -> str:
    """
    Get the content of README.txt attached to the installed dictionary.

    Parameters
    ----------
    db_dir: os.PathLike, optional
        The directory where the database files has been installed.
        If omitted, it will be determined by `get_db_dir()`.

    url: str, optional
        URL of the Jageocoder server endpoint.

    Returns
    -------
    str
        The content of the text.
    """
    if db_dir is None:
        if url is not None:
            return RemoteTree(url=url).installed_dictionary_readme()

        db_dir = get_db_dir(mode='r')

    readme_path = os.path.join(db_dir, "README.md")
    if not os.path.exists(readme_path):
        return "(no README information)"

    with open(readme_path, "r") as f:
        content = f.read()

    return content


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
    results = _tree.searchNode(query)

    if _tree.get_config('best_only'):
        if len(results) == 0:
            return {'matched': '', 'candidates': []}

        return {
            'matched': results[0][1],
            'candidates': [x[0].as_dict() for x in results],
        }

    result_by_matched = {}
    for result in results:
        if result.matched not in result_by_matched:
            result_by_matched[result.matched] = []

        result_by_matched[result.matched].append(result.node.as_dict())

    return [
        {"matched": r[0], "candidates": r[1]} for r in sorted(
            result_by_matched.items(),
            key=lambda x: len(x[0]),
            reverse=True
        )
    ]


def searchNode(query: str) -> List[Result]:
    """
    Searches for address nodes corresponding to an address notation
    and returns the matching substring and a list of nodes.

    Parameters
    ----------
    query : str
        An address notation to be searched.

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
    """  # noqa: E501
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    return _tree.searchNode(query)


def reverse(
    x: float,
    y: float,
    level: Optional[int] = None,
    as_dict: Optional[bool] = True
) -> list:
    """
    Reverse geocoding.

    Parameters
    ----------
    x: float
        Longitude of the point.
    y: float
        Latitude of the point.
    level: int, optional
        Target node level.
    as_dict: bool, default=True
        If True, returns candidates as dict objects.

    Returns
    -------
    list

    Notes
    -----
    - The result list contains up to 3 nodes.
    - Each element is a dict type with the following structure:
        {"candidate":AddressNode, "dist":float}
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    return _tree.reverse(x, y, level, as_dict)


def search_by_machiaza_id(
        id: str
) -> list:
    """
    Finds the corresponding address nodes from the "machiaza-id" of
    the address base registry.

    Parameters
    ----------
    id: str
        Machiaza-id.

    Returns
    -------
    List[AddressNode]

    Notes
    -----
    - If "id" is 12 characters, the first 5 characters are considered the JISX0402 code.
    - If "id" is 13 characters, the first 6 characters are considered the lg-code.
    - In either of the above cases, search for the address node whose machiaza-id
        matches the rest 7 characters in the corresponding municipality.
    - Otherwise, it searches for address nodes whose machiaza-id matches "id"
        from all municipalities. In this case, aza_id must be 7 characters.
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    return _tree.search_by_machiaza_id(id)


def search_by_postcode(
        code: str
) -> list:
    """
    Finds the corresponding address node from a postcode.

    Parameters
    ----------
    code: str
        The postal code as defined by the Japan Post.

    Returns
    -------
    List[AddressNode]

    Notes
    -----
    - The "code" must be 7 characters.
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    return _tree.search_by_postcode(code)


def search_by_prefcode(
        code: str
) -> list:
    """
    Finds the corresponding address nodes from the JISX0401 code
    or the prefacture's local-government code.

    Parameters
    ----------
    code: str
        Prefacture code as defined in JISX0401, of local government code defined by MIC.

    Returns
    -------
    List[AddressNode]

    Notes
    -----
    - If "code" is 2 characters, the code is considered the JISX0401 code.
    - If "code" is 6 characters, the code is considered the local-govenment code.
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    return _tree.search_by_prefcode(code)


def search_by_citycode(
        code: str
) -> list:
    """
    Finds the corresponding address nodes from the JISX0402 code
    or the local-government code.

    Parameters
    ----------
    code: str
        City code as defined in JISX0402, of local government code defined by MIC.

    Returns
    -------
    List[AddressNode]

    Notes
    -----
    - If "code" is 5 characters, the code is considered the JISX0402 code.
    - If "code" is 6 characters, the code is considered the local-govenment code.
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    return _tree.search_by_citycode(code)


def create_trie_index() -> None:
    """
    Create the TRIE index from the database file.

    This function is a shortcut for AddressTree.create_trie_index().
    """
    if not is_initialized():
        raise JageocoderError("Not initialized. Call 'init()' first.")

    global _tree
    if isinstance(_tree, RemoteTree):
        raise JageocoderError("Can't update TRIE index on remote server.")

    _tree.create_trie_index()


def version():
    return jageocoder.__version__


def dictionary_version():
    return jageocoder.__dictionary_version__
