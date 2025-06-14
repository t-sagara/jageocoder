import datetime
from logging import getLogger
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Optional, Set, Tuple, Union

from deprecated import deprecated

from .tree import get_db_dir, AddressTree
from jageocoder.address import AddressLevel
from jageocoder.aza_master import AzaMaster
from jageocoder.exceptions import AddressTreeException
from jageocoder.node import AddressNode, AddressNodeTable
from jageocoder.result import Result
from jageocoder.trie import AddressTrie, TrieNode

logger = getLogger(__name__)


class LocalTree(AddressTree):
    """
    The address-tree structure on the local database.

    Attributes
    ----------
    mode: str
        Read (r) or Write (w).
    db_dir: PathLike
        Directory path where the database files are located.
    table: AddressNodeTable
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

    def __init__(
        self,
        db_dir: Optional[os.PathLike] = None,
        mode: str = 'a',
        debug: Optional[bool] = None,
        **kwargs,
    ):
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
        super().__init__(debug=debug)

        # Set default values
        self.mode = mode
        if db_dir is None:
            db_dir = get_db_dir(mode)
        else:
            db_dir = Path(db_dir).absolute()

        if db_dir is None:
            msg = "Cannot choose a directory to create the database."
            raise AddressTreeException(msg)

        if db_dir.exists() and not db_dir.is_dir():
            msg = f"Specified path '{db_dir}' is not a directory."
            raise AddressTreeException(msg)

        if not db_dir.exists():
            if self.mode == "w":
                logger.info(f"Create directory '{db_dir}' for the database.")
                db_dir.mkdir(mode=0o755)
            else:
                msg = f"No database found at the specified path '{db_dir}'."
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

    def __not_in_readonly_mode(self) -> None:
        """
        Check if the dictionary is not opened in the read-only mode.

        If the mode is read-only, AddressTreeException will be raised.
        """
        if self.mode == 'r':
            raise AddressTreeException(
                'This method is not available in read-only mode.')

    @property
    def datasets(self) -> Optional[Dict[int, Any]]:
        """
        Get list of datasets installed in the dictionary.

        Returns
        -------
        List[Dataset]:
            List of datasets.
        """
        return self.address_nodes.datasets.get_all()

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
        node = self.address_nodes.get_record(pos=node_id)
        node.tree = self
        return node

    def count_records(self) -> int:
        """
        Get the number of records in the database.

        Returns
        -------
        int
        """
        return self.address_nodes.count_records()

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
        pattern = '{}:{}'.format(category, value)
        nodes: List[AddressNode] = self.address_nodes.search_records_on(
            attr="note", value=pattern)  # exact match
        for node in nodes:
            node.tree = self

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
        record = self.aza_masters.search_by_code(code, as_dict=True)
        return record

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
                        node = self.get_node_by_id(node_id=node_id)
                        if node.name == v:
                            return

                msg = "'{}' is not a valid value for {}.".format(v, key)
                raise RuntimeError(msg)

        else:
            return

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
    ) -> Dict[int, Tuple[AddressNode, str]]:
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
        _processed_nodes: Set[int] = processed_nodes or set()
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

                if node_id in _processed_nodes:
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
                    index=rest_index,
                    processed_nodes=_processed_nodes)
                _processed_nodes.add(node_id)
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

                    noname_child = self.get_node_by_id(node_id=node.id + 1)
                    if noname_child.name == AddressNode.NONAME and \
                            noname_child.id not in _processed_nodes:
                        _processed_nodes.add(noname_child.id)
                        # Search under NONAME oaza node.
                        for result in noname_child.search_recursive(
                            index=rest_index,
                            processed_nodes=_processed_nodes
                        ):
                            if len(result.matched) > 0:
                                results_by_node.append(result)
                                logger.debug(
                                    "Found '{}'({}) in NONAME Oaza.".format(
                                        result.get_node().name,
                                        result.get_node().id
                                    ))

                    self.set_config(aza_skip=aza_skip)

                for cand in results_by_node:
                    node = cand.get_node()
                    if len(target_area) > 0:
                        for area in target_area:
                            inside = node.is_inside(area)
                            if inside == 1:
                                break

                        if inside != 1:
                            msg = "Node {}({}) is not in the target area."
                            logger.debug(msg.format(node.name, node.id))
                            continue

                    if self.get_config("require_coordinates") \
                            and not node.has_valid_coordinate_values():
                        logger.debug("Node {}({}) has no coordinates.".format(
                            node.name, node.id
                        ))
                        continue

                    _len = offset + cand.nchars
                    _part = offset + len(cand.matched)
                    msg = "candidate: {} ({})"
                    logger.debug(msg.format(key + cand.matched, _len))
                    if best_only:
                        if _len > max_len:
                            results = {
                                node.id: (cand.get_node(), key + cand.matched)
                            }
                            max_len = _len
                            min_part = _part

                        elif _len == max_len and node.id not in results \
                                and (min_part is None or _part <= min_part):
                            results[node.id] = (
                                cand.get_node(), key + cand.matched)
                            min_part = _part

                    else:
                        if node.id in resolved_node_ids:
                            continue

                        cur = node.get_parent()
                        while cur is not None:
                            resolved_node_ids.add(cur.id)
                            cur = cur.parent

                        results[node.id] = (
                            node, key + cand.get_matched_string())
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
        retrieved: Tuple[AddressNode, str]
    ) -> str:
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
        recovered = ""
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
        if self.reverse_index is None:
            from jageocoder.rtree import Index
            self.reverse_index = Index(tree=self)

        return self.reverse_index.nearest(x=x, y=y, level=level, as_dict=as_dict)

    def installed_dictionary_version(self) -> str:
        """
        Get the installed dictionary version.

        Returns
        -------
        str
            The version string of the installed dicitionary or the server.
        """
        metadata_path = self.db_dir / "metadata.txt"
        if metadata_path.exists():
            with open(metadata_path, "r") as f:
                version = f.readline().rstrip()

        else:
            readme_path = self.db_dir / "README.md"
            if readme_path.exists():
                stats = os.stat(readme_path)
                version = datetime.date.fromtimestamp(
                    stats.st_mtime).strftime('%Y%m%d')
            else:
                version = '(Unknown)'

        return version

    def installed_dictionary_readme(self) -> str:
        """
        Get the content of README.txt attached to the installed dictionary.

        Returns
        -------
        str
            The content of the text.
        """
        readme_path = self.db_dir / "README.md"
        if not os.path.exists(readme_path):
            return "(no README information)"

        with open(readme_path, "r") as f:
            content = f.read()

        return content
