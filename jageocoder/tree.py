from collections import OrderedDict
from logging import getLogger
import os
from pathlib import Path
import re
import site
import sys
from typing import Any, Union, List, Set, Optional

from deprecated import deprecated

import jaconv
from jageocoder.address import AddressLevel
from jageocoder.aza_master import AzaMaster
from jageocoder.dataset import Dataset
from jageocoder.exceptions import AddressTreeException
from jageocoder.itaiji import Converter
from jageocoder.node import AddressNode, AddressNodeTable
from jageocoder.result import Result
from jageocoder.trie import AddressTrie, TrieNode

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
        db_dir = os.environ.get('JAGEOCODER_DB2_DIR')
        if db_dir.lower().startswith('http'):
            return db_dir

        db_dirs.append(Path(db_dir))

    db_dirs += [
        Path(sys.prefix) / 'jageocoder/db2/',
        Path(site.USER_BASE) / 'jageocoder/db2/',
    ]

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


class LRU(OrderedDict):
    'Limit size, evicting the least recently looked-up key when full'

    def __init__(self, maxsize=512, *args, **kwds):
        self.maxsize = maxsize
        super().__init__(*args, **kwds)

    def __getitem__(self, key):
        value = super().__getitem__(key)
        self.move_to_end(key)
        return value

    def __setitem__(self, key, value):
        if key in self:
            self.move_to_end(key)

        super().__setitem__(key, value)
        if len(self) > self.maxsize:
            oldest = next(iter(self))
            logger.debug("Delete '{}'".format(oldest))
            del self[oldest]


class AddressTree(object):
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

    def __init__(self,
                 db_dir: Optional[os.PathLike] = None,
                 mode: str = 'a',
                 debug: Optional[bool] = None):
        """
        The initializer

        Parameters
        ----------
        db_dir: os.PathLike, optional
            The database directory.
            If omitted, the directory returned by get_db_dir() is used.
            'address.db' and 'address.trie' are stored under this directory.

        mode: str, optional (default='a')
            Specifies the mode for opening the database.

            - In the case of 'a', if the database already exists,
              use it. Otherwize create a new one.

            - In the case of 'w', if the database already exists,
              delete it first. Then create a new one.

            - In the case of 'r', if the database already exists,
              use it. Otherwise raise a JageocoderError exception.

        debug: bool, optional (default=False)
            Debugging flag. If set to True, write debugging messages.
            If omitted, refer 'JAGEOCODER_DEBUG' environment variable,
            or False if the environment variable is also undefined.
        """
        # Set default values
        self.mode = mode
        if db_dir is None:
            db_dir = get_db_dir(mode)
        else:
            db_dir = Path(db_dir).absolute()

        if db_dir is None or not db_dir.is_dir():
            msg = "Directory '{}' does not exist.".format(db_dir)
            raise AddressTreeException(msg)

        self.db_dir = db_dir
        self.address_nodes: AddressNodeTable = AddressNodeTable(
            db_dir=self.db_dir)
        self.aza_masters: AzaMaster = AzaMaster(db_dir=self.db_dir)
        self.trie_nodes: TrieNode = self.get_trie_nodes()
        self.trie_path = db_dir / 'address.trie'

        # Options
        self.debug = debug or bool(os.environ.get('JAGEOCODER_DEBUG', False))

        # Clear database when in write mode.
        if self.mode == 'w':
            self.address_nodes.delete()
            if os.path.exists(self.trie_path):
                os.remove(self.trie_path)

        self.root = None
        self.trie = AddressTrie(self.trie_path)
        self.reverse_index = None

        # Regular expression
        self.re_float = re.compile(r'^\-?\d+\.?\d*$')
        self.re_int = re.compile(r'^\-?\d+$')
        self.re_address = re.compile(r'^(\d+);(.*)$')

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

        # Itaiji converter
        self.converter = Converter()

    def __not_in_readonly_mode(self) -> None:
        """
        Check if the dictionary is not opened in the read-only mode.

        If the mode is read-only, AddressTreeException will be raised.
        """
        if self.mode == 'r':
            raise AddressTreeException(
                'This method is not available in read-only mode.')

    @property
    def datasets(self) -> List[Dataset]:
        """
        Get list of datasets installed in the dictionary.

        Returns
        -------
        List[Dataset]:
            List of datasets.
        """
        return self.address_nodes.datasets.get_all()

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
        node = self.address_nodes.get_record(node_id)
        node.tree = self
        return node

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
        nodes = []
        pattern = '{}:{}'.format(category, value)
        nodes = self.address_nodes.search_records_on(
            attr="note", value=pattern)  # exact match

        return nodes

    def search_ids_by_codes(
            self,
            category: str,
            value: str) -> List[AddressNode]:
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
        ids = []
        pattern = '{}:{}'.format(category, value)
        ids = self.address_nodes.search_ids_on(
            attr="note", value=pattern)  # exact match

        return ids

    @deprecated("Use 'node.get_fullname()' instead of this method.")
    def get_node_fullname(self, node: Union[AddressNode, int]) -> List[str]:
        if isinstance(node, int):
            node = self.get_node_by_id(node)

        return node.get_fullname()

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

                # Check if the value is a name of node in the database.
                std = self.converter.standardize(v)
                candidates = self.trie.common_prefixes(std)
                if std in candidates:
                    trie_node_id = candidates[std]
                    for node_id in self.trie_nodes.get_record(
                            pos=trie_node_id).nodes:
                        node = self.address_nodes.get_record(pos=node_id)
                        if node.name == v:
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
        >>> jageocoder.get_module_tree().get_config('aza_skip')
        'off'
        >>> jageocoder.get_module_tree().get_config(['best_only', 'target_area'])
        {'best_only': True, 'target_area': []}
        >>> jageocoder.get_module_tree().get_config()
        {'debug': False, 'aza_skip': 'off', 'best_only': True, 'target_area': [], 'require_coordinates': False}
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

        return self.config[key]

    def get_trie_nodes(self) -> TrieNode:
        """
        Get the TRIE node table.

        Notes
        -----
        - Todo: If the trie index is not created, create.
        """
        return TrieNode(db_dir=self.db_dir)

    def search_by_tree(self, address_names: List[str]) -> AddressNode:
        """
        Get the corresponding node from the list of address element names,
        recursively search for child nodes using the tree.

        For example, ['東京都','新宿区','西新宿','二丁目'] will search
        the '東京都' node under the root node, search the '新宿区' node
        from the children of the '東京都' node. Repeat this process and
        return the '二丁目' node which is a child of '西新宿' node.

        Parameters
        ----------
        address_names : list of str
            A list of address element names to be searched.

        Return
        ------
        AddressNode:
            The node matched last.
        """
        cur_node = self.get_root()
        for name in address_names:
            name_index = self.converter.standardize(name)
            node = cur_node.get_child(name_index)
            if not node:
                break
            else:
                cur_node = node

        return cur_node

    def search_by_trie(
        self,
        query: str,
        processed_nodes: Optional[Set[int]] = None
    ) -> dict:
        """
        Get the list of corresponding nodes using the TRIE index.
        Returns a list of address element nodes that match
        the query string in the longest part from the beginning.

        For example, '中央区中央1丁目' will return the nodes
        corresponding to '千葉県千葉市中央区中央一丁目' and
        '神奈川県相模原市中央区中央一丁目'.

        Parameters
        ----------
        query : str
            An address notation to be searched.
        processed_nodes: Set of the AddressNode's id, optional
            List of node's id that have already been processed.

        Return
        ------
        A dict object whose key is a node id
        and whose value is a list of node and substrings
        that match the query.
        """
        logger.debug((
            "Called with query:'{}', processed_nodes:{}".format(
                query,
                processed_nodes
            )))
        index = self.converter.standardize(
            query, keep_numbers=True)
        index_for_trie = self.converter.standardize(query)
        candidates = self.trie.common_prefixes(index_for_trie)
        results = {}
        max_len = 0
        min_part = None
        best_only = self.get_config('best_only')
        target_area = self.get_config('target_area')

        keys = sorted(candidates.keys(),
                      key=len, reverse=True)

        logger.debug("Trie: {}".format(','.join(keys)))

        min_key = ''
        processed_nodes: Set[int] = processed_nodes or set()
        resolved_node_ids: Set[int] = set()

        for k in keys:
            if len(k) < len(min_key):
                logger.debug("Key '{}' is shorter than '{}'".format(
                    k, min_key))
                continue

            trie_id = candidates[k]
            logger.debug("Trie_id of key '{}' = {}".format(
                k, trie_id))
            trie_node = self.trie_nodes.get_record(pos=trie_id)
            offset = self.converter.match_len(index, k)
            key = index[0:offset]
            rest_index = index[offset:]
            for node_id in trie_node.nodes:
                node = self.get_node_by_id(node_id=node_id)

                if not node.has_valid_coordinate_values() \
                        and self.get_config('require_coordinates'):
                    node = node.add_dummy_coordinates()

                if min_key == '' and node.level <= AddressLevel.WARD:
                    # To make the process quicker, once a node higher
                    # than the city level is found, addresses shorter
                    # than the node are not searched after this.
                    logger.debug((
                        "A node with ward or higher levels found. "
                        "Set min_key to '{}'").format(k))
                    min_key = k

                if node_id in processed_nodes:
                    logger.debug("Node {}({}) already processed.".format(
                        node.name, node.id))
                    continue

                if len(target_area) > 0:
                    # Check if the node is inside the specified area
                    for area in target_area:
                        inside = node.is_inside(area)
                        if inside in (1, -1):
                            break

                    if inside == 0:
                        msg = "Node {}({}) is not in the target area."
                        logger.debug(msg.format(node.name, node.id))
                        continue

                logger.debug((
                    "Search for the node with the longest match "
                    "to the remaining '{}' recursively, "
                    "starting with node '{}'(id:{})."
                ).format(
                    rest_index, node.name, node.id))
                results_by_node = node.search_recursive(
                    tree=self,
                    index=rest_index,
                    processed_nodes=processed_nodes)
                processed_nodes.add(node_id)
                logger.debug('{}({}) marked as processed'.format(
                    node.name, node.id))

                if len(results_by_node[0].matched) == 0 and \
                        node.level == AddressLevel.CITY and \
                        not rest_index.startswith(AddressNode.NONAME):

                    logger.debug(
                        "Search for NONAME Oaza of '{}'({})".format(
                            node.name, node.id
                        ))

                    aza_skip = self.get_config('aza_skip')
                    for result in results.values():
                        if result[1].startswith(key) and result[1] > key:
                            self.set_config(aza_skip=False)
                            logger.debug(
                                "Since one or more candidates are found, "
                                "no omission of Aza will be checked."
                            )
                            break

                    noname_child = node.table.get_record(pos=node.id + 1)
                    if noname_child.name == AddressNode.NONAME and \
                            noname_child.id not in processed_nodes:
                        processed_nodes.add(noname_child.id)
                        # Search under NONAME oaza node.
                        for result in noname_child.search_recursive(
                            tree=self,
                            index=rest_index,
                            processed_nodes=processed_nodes
                        ):
                            if len(result.matched) > 0:
                                results_by_node.append(result)
                                logger.debug(
                                    "Found '{}'({}) in NONAME Oaza.".format(
                                        result.node.name, result.node.id
                                    ))

                    self.set_config(aza_skip=aza_skip)

                for cand in results_by_node:
                    if len(target_area) > 0:
                        for area in target_area:
                            inside = cand.node.is_inside(area)
                            if inside == 1:
                                break

                        if inside != 1:
                            msg = "Node {}({}) is not in the target area."
                            logger.debug(msg.format(
                                cand.node.name, cand.node.id))
                            continue

                    if self.get_config("require_coordinates") \
                            and not cand.node.has_valid_coordinate_values():
                        logger.debug("Node {}({}) has no coordinates.".format(
                            cand.node.name, cand.node.id
                        ))
                        continue

                    _len = offset + cand.nchars
                    _part = offset + len(cand.matched)
                    msg = "candidate: {} ({})"
                    logger.debug(msg.format(key + cand.matched, _len))
                    if best_only:
                        if _len > max_len:
                            results = {
                                cand.node.id: [cand.node, key + cand.matched]
                            }
                            max_len = _len
                            min_part = _part

                        elif _len == max_len and cand.node.id not in results \
                                and (min_part is None or _part <= min_part):
                            results[cand.node.id] = [
                                cand.node, key + cand.matched]
                            min_part = _part

                    else:
                        if cand.node.id in resolved_node_ids:
                            continue

                        cur = cand.node.parent
                        while cur is not None:
                            resolved_node_ids.add(cur.id)
                            cur = cur.parent

                        results[cand.node.id] = [cand.node, key + cand[1]]
                        max_len = max(_len, max_len)
                        if min_part is None:
                            min_part = _part
                        else:
                            min_part = min(min_part, _part)

        return results

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
        node = self.address_nodes.get_record(pos=id)
        node.tree = self
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
        [[[11460207:東京都(139.69178,35.68963)1(lasdec:130001/jisx0401:13)]>[12063502:多摩市(139.446366,35.636959)3(jisx0402:13224)]>[12065383:落合(139.427097,35.624877)5(None)]>[12065384:一丁目(139.427097,35.624877)6(None)]>[12065390:15番地(139.428969,35.625779)7(None)], '多摩市落合1-15-']]
        """  # noqa: E501
        results = self.search_by_trie(query=query)
        values = sorted(results.values(), reverse=True,
                        key=lambda v: len(v[1]))

        matched_substring = {}
        results = []
        for v in values:
            if v[1] in matched_substring:
                matched = matched_substring[v[1]]
            else:
                matched = self._get_matched_substring(query, v)
                matched_substring[v[1]] = matched

            results.append(Result(v[0], matched))

        # Sort the result list in descending order of the length of the match
        # and ascending order of the node priority.
        results.sort(
            key=lambda r: len(r.matched) * -100 + r.node.priority)

        return results

    def _get_matched_substring(
            self, query: str,
            retrieved: list) -> str:
        """
        From the matched standardized substring,
        recover the corresponding substring of
        the original search string.

        Parameters
        ----------
        query : str
            The original search string.
        matchd : str
            The matched standardized substring.

        Return
        ------
        str:
            The recovered substring.
        """
        recovered = None
        node, matched = retrieved
        l_result = len(matched)
        pos = l_result if l_result <= len(query) else len(query)
        pos_history = [pos]

        while True:
            substr = query[0:pos]
            standardized = self.converter.standardize(
                substr, keep_numbers=True)
            l_standardized = len(standardized)

            if l_standardized == l_result:
                recovered = substr
                break

            if l_standardized <= l_result:
                pos += 1
            else:
                pos -= 1

            if pos < 0 or pos > len(query):
                break

            if pos in pos_history:
                message = "Can't de-standardize matched {} in {}".format(
                    matched, query)
                raise AddressTreeException(message)

        if pos < len(query) and node.name != '':
            if query[pos] == node.name[-1] and \
                    len(self.converter.standardize(
                        query[0:pos+1])) == l_result:
                # When the last letter of a node name is omitted
                # by normalization, and if the query string contains
                # that letter, it is determined to have matched
                # up to that letter.
                # Ex. "兵庫県宍粟市山崎町上ノ１５０２" will match "上ノ".
                recovered = query[0:pos+1]
            elif query[-2:] in ('通り', '通リ'):
                # '通' can be expressed as '通り'
                recovered = query[0:pos+1]

        return recovered

    def create_note_index_table(self) -> None:
        """
        Collect notes from all address elements and create
        search table with index.
        """
        self.__not_in_readonly_mode()
        self.address_nodes.create_indexes()

    def reverse(
        self,
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
        if self.reverse_index is None:
            from jageocoder.rtree import Index
            self.reverse_index = Index(tree=self)

        return self.reverse_index.nearest(x=x, y=y, level=level, as_dict=as_dict)

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
            candidates = self.search_ids_by_codes(
                category="aza_id",
                value=id[-7:])
            nodes = [self.address_nodes.get_record(x)
                     for x in candidates
                     if x >= citynode.id and x < citynode.sibling_id]
        elif len(id) == 13:
            # lasdec(6digits) + aza_id(7digits)
            citynode = self.search_by_citycode(code=id[0:6])
            if len(citynode) == 0:
                return []

            citynode = citynode[0]
            candidates = self.search_ids_by_codes(
                category="aza_id",
                value=id[-7:])
            nodes = [self.address_nodes.get_record(x)
                     for x in candidates
                     if x >= citynode.id and x < citynode.sibling_id]
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
