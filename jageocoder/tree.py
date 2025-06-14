from __future__ import annotations
from abc import ABC
from logging import getLogger
import os
from pathlib import Path
import re
import site
import sys
from typing import Any, Dict, List, Optional, Union

from deprecated import deprecated

import jaconv
from jageocoder.exceptions import AddressTreeException
from jageocoder.itaiji import Converter
from jageocoder.node import AddressNode
from jageocoder.result import Result

logger = getLogger(__name__)


def get_db_dir(mode: str = 'r') -> Optional[Path]:
    """
    Get the database directory.

    Parameters
    ----------
    mode: str, optional(default='r')
        Specifies the mode for searching the database directory.
        If 'a' or 'w' is set, search a writable directory.
        If 'r' is set, search a database file that already exists.

    Return
    ------
    Path or None
        The path to the database directory.
        If no suitable directory is found, raise an AddressTreeException.

    Notes
    -----
    This method searches a directory in the following order of priority.
    - 'JAGEOCODER_DB_DIR' environment variable
    - '(sys.prefix)/jageocoder/db2/'
    - '(site.USER_BASE)/jageocoder/db2/'
    """
    if mode not in ('a', 'w', 'r'):
        raise AddressTreeException(
            'Invalid mode value. Specify one of "a", "w", or "r".')

    db_dirs: List[Path] = []
    if 'JAGEOCODER_DB2_DIR' in os.environ:
        db_dir = os.environ.get('JAGEOCODER_DB2_DIR', "")
        if db_dir.lower().startswith('http'):
            raise AddressTreeException('An url is set to `JAGEOCODER_DB2_DIR`')

        db_dirs.append(Path(db_dir))

    db_dirs.append(Path(sys.prefix) / 'jageocoder/db2/')
    if isinstance(site.USER_BASE, str):
        db_dirs.append(Path(site.USER_BASE) / 'jageocoder/db2/')

    for db_dir in db_dirs:
        path = db_dir / 'address_node'
        if path.exists():
            return db_dir

        if mode == 'r':
            continue

        try:
            path = "__write_test__"
            os.makedirs(db_dir, mode=0o777, exist_ok=True)
            with open(path, 'a') as fp:
                fp.write("test")

            os.remove(path)
            return db_dir
        except (FileNotFoundError, PermissionError):
            continue

    if mode in ('a', 'w',):
        raise AddressTreeException(
            "Cannot find a directory where the database can be created."
        )

    return None  # In case of read-only mode.


class AddressTree(ABC):
    """
    The address-tree structure.

    Attributes
    ----------
    mode: str
        Read (r) or Write (w).
    db_dir: PathLike
        Directory path where the database files are located.
    address_nodes: AddressNodeTable
        Table of address-nodes.
    aza_masters: AzaMaster
        Aza master table from the Address Base registry.
    trie_nodes: TrieNode
        Table of trie-nodes.
    trie_path: PathLike
        Path to the AddressTrie file.
    debug: bool
        Debug mode flag.
    root: AddressTrie
        The root-node of the address TRIE index.
    config: dict
        Configuration parameters.
    converter: itaiji.Converter
        Converter object of character-variants.
    """

    def __new__(
            cls,
            db_dir: Optional[os.PathLike] = None,
            mode: str = "r",
            url: Optional[str] = None,
            *args, **kwargs
    ) -> AddressTree:
        from .local_tree import LocalTree
        from .remote import RemoteTree

        if cls is AddressTree:
            if db_dir is not None:
                return LocalTree.__new__(LocalTree, db_dir=db_dir, mode=mode, *args, **kwargs)

            if url is not None:
                return RemoteTree.__new__(RemoteTree, url=url, *args, **kwargs)

            _db_dir = get_db_dir(mode)
            if _db_dir is not None:
                return LocalTree.__new__(LocalTree, db_dir=_db_dir, mode=mode, **kwargs)

            _url = os.environ.get("JAGEOCODER_SERVER_URL")
            if _url is not None and mode == "r":
                return RemoteTree.__new__(RemoteTree, url=_url, **kwargs)

            raise AddressTreeException(
                "Specify 'db_dir' or 'url' to instanciate AddressTree."
            )

        return super().__new__(cls)

    def __init__(
        self,
        db_dir: Optional[os.PathLike] = None,
        mode: str = "r",
        url: Optional[str] = None,
        debug: Optional[bool] = None
    ):
        """
        The initializer

        Parameters
        ----------
        debug: bool, optional (default=False)
            Debugging flag. If set to True, write debugging messages.
            If omitted, refer 'JAGEOCODER_DEBUG' environment variable,
            or False if the environment variable is also undefined.
        """
        # Options
        self.debug = debug or bool(os.environ.get('JAGEOCODER_DEBUG', False))

        # Itaiji converter
        self.converter = Converter()

        # Set default settings
        self.config = {
            'debug': False,
            'aza_skip': None,
            'best_only': True,
            'target_area': [],
            'require_coordinates': True,
            'auto_redirect': True,
        }
        self.set_config(**{
            'debug': self.debug,
            'aza_skip': os.environ.get(
                'JAGEOCODER_OPT_AZA_SKIP', self.config["aza_skip"]),
            'best_only': os.environ.get(
                'JAGEOCODER_OPT_BEST_ONLY', self.config["best_only"]),
            'target_area': os.environ.get(
                'JAGEOCODER_OPT_TARGET_AREA', self.config["target_area"]),
            'require_coordinates': os.environ.get(
                'JAGEOCODER_OPT_REQUIRE_COORDINATES',
                self.config["require_coordinates"]),
            'auto_redirect': os.environ.get(
                'JAGEOCODER_OPT_AUTO_REDIRECT',
                self.config["auto_redirect"]),
        })

    @property
    def datasets(self) -> Optional[Dict[int, Any]]:
        """
        Get list of datasets installed in the dictionary.

        Returns
        -------
        Dict[int, Any]:
            List of datasets.
        """
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    def get_root(self) -> AddressNode:
        """
        Get the root-node of the tree.
        If not set yet, create and get the node from the database.

        Returns
        -------
        AddressNode:
            The root node object.
        """
        return self.get_node_by_id(
            node_id=AddressNode.ROOT_NODE_ID
        )

    def get_version(self) -> str:
        """
        Get the version of the tree file.

        Return
        ------
        str:
            The version string.
        """
        root_node = self.get_root()
        if root_node.note is None:
            return "(no version)"

        return root_node.note

    def get_node_by_id(self, node_id: int) -> AddressNode:
        """
        Get the full node information by its id.

        Parameters
        ----------
        node_id: int
            The target node id.

        Returns
        -------
        AddressNode
        """
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    def count_records(self) -> int:
        """
        Get the number of records in the database.

        Returns
        -------
        int
        """
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    def search_nodes_by_codes(
            self,
            category: str,
            value: str) -> List[AddressNode]:
        """
        Search nodes by category and value.

        Parameters
        ----------
        category: str
            Category name such as 'jisx0402' or 'postcode'.
        value: str
            Target value.

        Returns
        -------
        List[AddressNode]
        """
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    def search_ids_by_codes(
            self,
            category: str,
            value: str) -> List[int]:
        """
        Search node ids by category and value.

        Parameters
        ----------
        category: str
            Category name such as 'jisx0402' or 'postcode'.
        value: str
            Target value.

        Returns
        -------
        List[int]
        """
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    @deprecated(reason="Rename to 'search_aza_record_by_code'.", version="2.1.10")
    def search_aza_records_by_codes(self, code: str) -> Dict[str, Union[bool, int, str]]:
        return self.search_aza_record_by_code(code)

    def search_aza_record_by_code(self, code: str) -> Dict[str, Union[bool, int, str]]:
        """
        Search Address-base-registry's aza records.

        Parameters
        ----------
        code: str
            Machi-aza code in ABR.

        Returns
        -------
        AzaRecord
        """
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    @deprecated("Use 'node.get_fullname()' instead of this method.")
    def get_node_fullname(self, node: Union[AddressNode, int]) -> List[str]:
        if isinstance(node, int):
            node = self.get_node_by_id(node)

        fullname = node.get_fullname(delimiter=None)
        if isinstance(fullname, str):
            raise AddressTreeException(
                "`get_fullname` returns a list of strings.")

        return fullname

    def set_config(self, **kwargs):
        """
        Set configuration parameters.

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
        for k, v in kwargs.items():
            self._set_config(k, v)

    def validate_config(self, key: str, value: Any) -> None:
        """
        Validate configuration key and parameters.

        Parameters
        ----------
        key: str
            The name of the parameter.
        value: str, int, bool, None
            The value to be set to the parameter.

        Notes
        -----
        If the key-value pair is not valid, raise RuntimeError.
        """
        if key == 'target_area':
            if value in (None, []):
                return

            if isinstance(value, str):
                value = [value]

            for v in value:
                if re.match(r'\d{2}', v) or re.match(r'\d{5}', v):
                    return

                msg = "'{}' is not a valid value for {}.".format(v, key)
                raise RuntimeError(msg)

        else:
            return

    def _set_config(
            self, key: str,
            value: Any):
        """
        Set configuration parameters.

        Parameters
        ----------
        key: str
            The name of the parameter.
        value: str, int, bool, None
            The value to be set to the parameter.
        """
        curval = self._get_config(key)
        if isinstance(curval, str):
            if value is None or isinstance(value, (bool, int)):
                value = str(value)
            elif isinstance(value, str):
                pass
            else:
                msg = "The value for '{}' must be a string but {}."
                raise RuntimeError(msg.format(key, type(value)))
        elif curval is None or isinstance(curval, bool):
            if value is None or isinstance(value, bool):
                pass
            elif isinstance(value, int):
                if value == 0:
                    value = False
                else:
                    value = True
            elif isinstance(value, str):
                if value.lower() in ('on', 'enable', 'true', 'yes'):
                    value = True
                elif value.lower() in ('off', 'disable', 'false', 'no'):
                    value = False
                elif value.lower() in ('auto', 'none', ''):
                    value = None
                else:
                    msg = ("The value '{}' for '{}' cannot be recognized "
                           "as bool or None.")
                    raise RuntimeError(msg.format(value, key))
            else:
                msg = "The value for '{}' must be a bool but {}."
                raise RuntimeError(msg.format(key, type(value)))
        elif isinstance(curval, int):
            if isinstance(value, bool):
                if value is False:
                    value = 0
                else:
                    value = 1
            elif isinstance(value, int):
                pass
            elif isinstance(value, str):
                if value.lower() in ('on', 'enable', 'true'):
                    value = 1
                elif value.lower() in ('off', 'disable', 'false'):
                    value = 0
                else:
                    try:
                        value = int(value)
                    except ValueError:
                        msg = ("The value '{}' for '{}' cannot be recognized "
                               "as int.")
                        raise RuntimeError(msg.format(value, key))
            else:
                msg = "The value for '{}' must be an integer but {}."
                raise RuntimeError(msg.format(key, type(value)))
        elif isinstance(curval, list):
            if value is None:
                value = []
            elif isinstance(value, (bool, int,)):
                value = [str(value)]
            elif isinstance(value, str):
                value = [x for x in value.split(',') if x != '']
            elif isinstance(value, list):
                pass
            else:
                msg = "The value for '{}' must be a list but {}."
                raise RuntimeError(msg.format(key, type(value)))

        if not isinstance(value, str) and isinstance(value, list):
            for v in value:
                self.validate_config(key, v)

        else:
            self.validate_config(key, value)

        self.config[key] = value
        return value

    def get_config(self, keys: Union[str, List[str], None] = None):
        """
        Get configurable parameter(s).

        Parameters
        ----------
        keys: str, List[str], optional
            If a name of parameter is specified, return its value.
            Otherwise, a dict of specified key and its value pairs
            will be returned.

        Returns
        -------
        Any, or dict.

        Examples
        --------

        >>> import jageocoder
        >>> jageocoder.init()
        >>> jageocoder.get_module_tree().set_config(aza_skip=True)
        >>> jageocoder.get_module_tree().get_config('aza_skip')
        True
        >>> jageocoder.get_module_tree().get_config(['best_only', 'target_area'])
        {'best_only': True, 'target_area': []}
        >>> jageocoder.get_module_tree().get_config()
        {'debug': False, 'aza_skip': True, 'best_only': True, 'target_area': [], 'require_coordinates': True, 'auto_redirect': True}
        """  # noqa: E501
        if keys is None:
            return self.config

        if isinstance(keys, str):
            return self._get_config(keys)

        config = {}
        for k in keys:
            config[k] = self._get_config(k)

        return config

    def _get_config(self, key: str):
        if key not in self.config:
            raise RuntimeError(
                "The config key '{}' does not exist.".format(key))

        v = self.config[key]
        return v

    @deprecated(reason="Use 'get_node_by_id'.", version="2.1.7")
    def get_address_node(self, id: int) -> AddressNode:
        """
        Get address node from the tree by its id.

        Parameters
        ----------
        id: int
            The node id.

        Returns
        -------
        AddressNode
            Node with the specified ID.
        """
        node = self.get_node_by_id(node_id=id)
        return node

    @deprecated(('Renamed to `searchNode()` because it was confusing'
                 ' with jageocoder.search()'))
    def search(self, query: str, **kwargs) -> list:
        return self.searchNode(query, **kwargs)

    def searchNode(self, query: str) -> List[Result]:
        """
        Searches for address nodes corresponding to an address notation
        and returns the matching substring and a list of nodes.

        Parameters
        ----------
        query : str
            An address notation to be searched.

        Return
        ------
        list:
            A list of AddressNode and matched substring pairs.

        Example
        -------
        >>> import jageocoder
        >>> jageocoder.init()
        >>> tree = jageocoder.get_module_tree()
        >>> tree.searchNode('多摩市落合1-15-2')
        [{"node": {"id": ..., "name": "2", "name_index": "2.", "x": 139.4..., "y": 35.6..., "level": 8, "priority": 9, "note": "", "parent_id": ..., "sibling_id": ...}, "matched": "多摩市落合1-15-2"}]
        """  # noqa: E501
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    def create_note_index_table(self) -> None:
        """
        Collect notes from all address elements and create
        search table with index.
        """
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    def reverse(
        self,
        x: float,
        y: float,
        level: Optional[int] = None,
        as_dict: Optional[bool] = True
    ) -> List[Dict[str, Union[AddressNode, float]]]:
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
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    @classmethod
    def _clean_numerical_string(cls, code: str) -> str:
        """
        Clean numeric string.
        """
        code = jaconv.zen2han(code, kana=False, ascii=False, digit=True)
        code = re.sub(r'\D', '', code)
        return code

    def search_by_machiaza_id(
            self,
            id: str
    ) -> List[AddressNode]:
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
        id = self._clean_numerical_string(id)
        if len(id) == 12:
            # jisx0402(5digits) + aza_id(7digits)
            citynode = self.search_by_citycode(code=id[0:5])
            if len(citynode) == 0:
                return []

            citynode = citynode[0]
            candidates = self.search_nodes_by_codes(
                category="aza_id",
                value=id[-7:])
            nodes = []
            for node in candidates:
                if node.id >= citynode.id and node.id < citynode.sibling_id:
                    nodes.append(node)

        elif len(id) == 13:
            # lasdec(6digits) + aza_id(7digits)
            citynode = self.search_by_citycode(code=id[0:6])
            if len(citynode) == 0:
                return []

            citynode = citynode[0]
            candidates = self.search_nodes_by_codes(
                category="aza_id",
                value=id[-7:])
            nodes = []
            for node in candidates:
                if node.id >= citynode.id and node.id < citynode.sibling_id:
                    nodes.append(node)

        else:
            nodes = self.search_nodes_by_codes(
                category="aza_id",
                value=id)

        return nodes

    def search_by_postcode(
            self,
            code: str
    ) -> List[AddressNode]:
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
        code = self._clean_numerical_string(code)
        if len(code) == 7:
            # Postcode(7digits)
            return self.search_nodes_by_codes(
                category="postcode",
                value=code)

        return []

    def search_by_prefcode(
            self,
            code: str
    ) -> List[AddressNode]:
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
        code = self._clean_numerical_string(code)
        if len(code) == 2:
            # jisx0401(2digits)
            return self.search_nodes_by_codes(
                category="jisx0401",
                value=code)

        elif len(code) == 6:
            # lg-code(6digits)
            return self.search_nodes_by_codes(
                category="jisx0401",
                value=code[0:2])

        return []

    def search_by_citycode(
            self,
            code: str
    ) -> List[AddressNode]:
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
        code = self._clean_numerical_string(code)
        if len(code) == 5:
            # jisx0402(5digits)
            return self.search_nodes_by_codes(
                category="jisx0402",
                value=code)

        elif len(code) == 6:
            # lg-code(6digits)
            return self.search_nodes_by_codes(
                category="jisx0402",
                value=code[0:5])

        return []

    def installed_dictionary_version(self) -> str:
        """
        Get the installed dictionary version.

        Returns
        -------
        str
            The version string of the installed dicitionary or the server.
        """
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")

    def installed_dictionary_readme(self) -> str:
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
        raise NotImplementedError(
            f"This method is not implemented for class '{self.__class__}'")
