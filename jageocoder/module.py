import datetime
import logging
import os
import shutil
from typing import Any, Dict, Optional, Union, List
import urllib.request
from urllib.error import URLError

import jageocoder

from jageocoder.exceptions import JageocoderError
from jageocoder.local_tree import LocalTree
from jageocoder.tree import AddressTree, get_db_dir
from jageocoder.remote import RemoteTree
from jageocoder.result import Result

_tree: Optional[AddressTree] = None  # The default AddressTree
logger = logging.getLogger(__name__)


def init(
    db_dir: Optional[os.PathLike] = None,
    mode: str = 'r',
    debug: Optional[bool] = None,
    url: Optional[str] = None,
    **kwargs
) -> None:
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

    _tree = AddressTree(
        db_dir=db_dir,
        mode=mode,
        url=url,
        debug=debug,
        **kwargs,
    )
    set_search_config(**kwargs)
    return

    # Check parameters
    if db_dir is not None:
        _db_dir = db_dir
    elif url != "" and mode == 'r':
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
        _tree = LocalTree(db_dir=_db_dir, mode=mode, debug=debug)
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
    return get_module_tree().set_config(**kwargs)


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
    return get_module_tree().get_config(keys)


def is_initialized() -> bool:
    """
    Checks if the module has been initialized with `init()`.

    Return
    ------
    bool
        True if the module is initialized, otherwise False.
    """
    try:
        get_module_tree()
        return True
    except JageocoderError:
        return False


def get_module_tree() -> AddressTree:
    """
    Get the module-level AddressTree singleton object.

    Return
    ------
    AddressTree
        The singleton object.
    """
    global _tree
    if _tree is None:
        raise JageocoderError("Tree is not initialized")

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
        if db_dir is None:
            raise JageocoderError(
                "Cannot find a directory to install the dictionary.")

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
        if db_dir is None:
            logger.info("Dictionary has not been installed.")
            return

    # Remove the directory
    logger.info('Removing directory {}'.format(db_dir))
    import shutil
    shutil.rmtree(db_dir)
    logger.info('Dictionary has been uninstalled.')


def get_datasets() -> Dict[int, Any]:
    """
    Get the datasets in the installed dictionary.

    Parameters
    ----------
    db_dir: os.PathLike, optional
        The directory where the database files has been installed.
        If omitted, it will be determined by `get_db_dir()`.

    Returns
    -------
    dict[int, dict]
        The map of the datasets with their ids as keys.
    """
    datasets = get_module_tree().datasets
    if datasets is None:
        raise JageocoderError("Datasets returns None.")

    return datasets


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
    tree = AddressTree(db_dir=db_dir, url=url)
    return tree.installed_dictionary_version()


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
    tree = AddressTree(db_dir=db_dir, url=url)
    return tree.installed_dictionary_readme()


def search(query: str) -> Union[Dict[str, Any], List[Dict[str, Any]]]:
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
    tree = get_module_tree()
    results = tree.searchNode(query)

    if tree.get_config('best_only'):
        if len(results) == 0:
            return {'matched': '', 'candidates': []}

        return {
            'matched': results[0].get_matched_string(),
            'candidates': [x.get_node().as_dict() for x in results],
        }

    result_by_matched = {}
    for result in results:
        if result.matched not in result_by_matched:
            result_by_matched[result.matched] = []

        result_by_matched[result.matched].append(result.get_node().as_dict())

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
    [{"node": {"id": ..., "name": "2", "name_index": "2.", "x": 139.4..., "y": 35.6..., "level": 8, "priority": 9, "note": "", "parent_id": ..., "sibling_id": ...}, "matched": "多摩市落合1-15-2"}]
    """  # noqa: E501
    return get_module_tree().searchNode(query)


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
    return get_module_tree().reverse(x, y, level, as_dict)


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
    return get_module_tree().search_by_machiaza_id(id)


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
    return get_module_tree().search_by_postcode(code)


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
    return get_module_tree().search_by_prefcode(code)


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
    return get_module_tree().search_by_citycode(code)


def search_aza_record_by_code(code: str) -> dict:
    """
    Search Address-base-registry's aza record.

    Parameters
    ----------
    code: str
        Machi-aza code in ABR.

    Returns
    -------
    dict
    """
    return get_module_tree().search_aza_record_by_code(code)


def create_trie_index() -> None:
    """
    Create the TRIE index from the database file.

    This function is a shortcut for AddressTree.create_trie_index().
    """
    tree = get_module_tree()
    if isinstance(tree, RemoteTree):
        raise JageocoderError("Can't update TRIE index on remote server.")

    if isinstance(tree, LocalTree):
        t: LocalTree = tree
        t.create_note_index_table()


def version():
    return jageocoder.__version__


def dictionary_version():
    return jageocoder.__dictionary_version__
