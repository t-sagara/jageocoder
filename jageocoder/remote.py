from __future__ import annotations
from collections import OrderedDict
import json
from logging import getLogger
import os
from typing import Any, Dict, List, NoReturn, Optional, Tuple, Union
import uuid

import requests

from jageocoder.address import AddressLevel
from jageocoder.exceptions import RemoteTreeException
from jageocoder.node import AddressNode
from jageocoder.result import Result
from jageocoder.tree import AddressTree


logger = getLogger(__name__)


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


class RemoteDataset(object):

    def __init__(self, tree: RemoteTree) -> None:
        self.tree = tree
        self.records = {}
        self._map: Optional[Dict[int, Any]] = None

    def load_record(self, id: int) -> None:
        rpc_result = self.tree.json_request(
            method="dataset.get",
            params={"id": id},
        )
        if self._map is None:
            self._map = {}

        self._map[rpc_result["id"]] = rpc_result
        return rpc_result

    def load_records(self) -> Dict[int, Dict[str, Union[int, str]]]:
        rpc_result = self.tree.json_request(
            method="dataset.get_all",
            params=[],
        )
        new_map = {}
        for v in rpc_result.values():
            # The keys of rpc_result are string, so convert to integer here
            new_map[v["id"]] = v

        self._map = new_map
        return new_map

    def get(self, id: int) -> dict:
        if self._map is None:
            try:
                self.load_records()
            except RemoteTreeException:
                self._map = {}

        if self._map is None:
            raise RemoteTreeException("Unexpected error")

        try:
            dataset = self.load_record(id)
            self._map[id] = dataset
        except RemoteTreeException:
            raise RemoteTreeException(
                f"Remote tree has no dataset for id={id}")

        if self._map is not None and id in self._map:
            return self._map[id]

        raise KeyError(f"'{id}' is not in the dataset keys.")

    def get_all(self) -> Optional[Dict[int, Dict[str, Union[int, str]]]]:
        if self._map is None:
            self.load_records()

        return self._map


class RemoteNodeTable(object):

    def __init__(self, tree: RemoteTree) -> None:
        self.tree = tree
        self.datasets = RemoteDataset(tree=tree)
        self.cache = LRU()
        self.server_signature: str = ""
        self.mode = 'r'   # Always read only

    def update_server_signature(self) -> str:
        """
        Update the remote server's signature.

        Note
        ----
        - This method must be called before any processing
            that requires dictionary consistency to ensure
            the server has not been restarted during processing.
        """
        server_signature = self.tree.json_request(
            method="jageocoder.server_signature",
            params=[],
        )
        if self.server_signature != server_signature:
            # The remote server has been restarted
            self.cache.clear()
            self.server_signature = str(server_signature)

        return self.server_signature

    def get_record(self, pos: int) -> AddressNode:
        """
        Get the record at the specified position from the remote server
        and convert it to AddressNode object.

        Parameters
        ----------
        pos: int
            The position.

        Returns
        -------
        AddressNode
            The converted object.
        """
        if pos in self.cache:
            return self.cache[pos]

        rpc_result = self.tree.json_request(
            method="node.get_record",
            params={"pos": pos, "server": self.server_signature},
        )
        node = AddressNode(**rpc_result)
        self.cache[pos] = node
        return node

    def count_records(self) -> int:
        """
        Get the number of records in the remote server.

        Returns
        -------
        int
        """
        rpc_result = self.tree.json_request(
            method="node.count_records",
            params=[],
        )
        return rpc_result

    def search_records_on(
            self,
            attr: str,
            value: str,
            funcname: str = "get") -> List[AddressNode]:
        """
        Search value from the table on the specified attribute on the remote server.

        Paramters
        ---------
        attr: str
            The name of target attribute.
        value: str
            The target value.
        funcname: str
            The name of search method.
            - "get" searches for records that exactly match the value.
            - "prefixes" searches for records that contained in the value.
            - "keys" searches for records that containing the value.

        Returns
        -------
        List[AddressNode]
            List of nodes.

        Notes
        -----
        - TRIE index must be created on the column before searching.
        - The TRIE index file will be automatically opened if it exists.
        """
        rpc_result = self.tree.json_request(
            method="node.search_records_on",
            params={
                "attr": attr,
                "value": value,
                "funcname": funcname,
                "server": self.server_signature
            },
        )
        nodes = []
        for record in rpc_result:
            node = AddressNode(**record)
            nodes.append(node)

        return nodes

    def search_ids_on(
        self,
        attr: str,
        value: str,
    ) -> List[int]:
        """
        Search id from the table on the specified attribute on the remote server.

        Paramters
        ---------
        attr: str
            The name of target attribute.
        value: str
            The target value.

        Returns
        -------
        List[int]
            List of node ids.
        """
        rpc_result = self.tree.json_request(
            method="node.search_records_on",
            params={
                "attr": attr,
                "value": value,
                "funcname": "get",
                "server": self.server_signature
            },
        )
        ids = [record["id"] for record in rpc_result]
        return ids


class RemoteTree(AddressTree):
    """
    The proxy class for remote server's address-tree structure.

    Attributes
    ----------
    url: str
        Endpoint URL of the currently connected server.
    debug: bool
        Debug mode flag.
    address_nodes: jageocoder.remote.RemoteNodeTable
        A table that manages nodes information on the server.
    config: dict
        Current 'search_config' settings.
    """

    def __init__(
            self,
            url: str,
            debug: Optional[bool] = None,
            **kwargs,
    ) -> None:
        """
        The initializer

        Parameters
        ----------
        url: str
            The endpoint URL to the connecting server.

        debug: bool, optional (default=False)
            Debugging flag. If set to True, write debugging messages.
        """
        super().__init__(debug=debug)
        self.url = url
        self.address_nodes = RemoteNodeTable(tree=self)
        self._session = None
        self.config = {
            'debug': self.debug,
            'aza_skip': os.environ.get('JAGEOCODER_OPT_AZA_SKIP'),
            'best_only': os.environ.get('JAGEOCODER_OPT_BEST_ONLY', True),
            'target_area': os.environ.get('JAGEOCODER_OPT_TARGET_AREA', []),
            'require_coordinates': os.environ.get(
                'JAGEOCODER_OPT_REQUIRE_COORDINATES', True),
            'auto_redirect': os.environ.get(
                'JAGEOCODER_OPT_AUTO_REDIRECT', True),
        }

    @property
    def datasets(self) -> Optional[Dict[int, Any]]:
        """
        Get list of datasets installed in the dictionary.

        Returns
        -------
        Dict[int, Any]:
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
        _nodes = self.address_nodes.search_records_on(
            attr="note", value=pattern)  # exact match
        nodes = []
        for node in _nodes:
            node.tree = self
            nodes.append(node)

        return nodes

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
        Tuple[Tuple[int, str, str, str]]
        """
        rpc_result = self.json_request(
            method="aza_master.search_by_codes",
            params={
                "code": code,
            },
        )
        return rpc_result

    def json_request(
            self,
            method: str,
            params: object,
    ) -> Any:
        payload = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
            "id": str(uuid.uuid4()),
        }
        if self._session is None:
            logger.debug("Start a new HTTP session with the remote tree.")
            self._session = requests.Session()

        logger.debug(
            "Send JSON-RPC request ---\n" +
            json.dumps(payload, indent=2, ensure_ascii=False)
        )
        response = self._session.post(
            url=self.url,
            data=json.dumps(payload),
            headers={"Content-Type": "application/json"}
        ).json()

        if "error" in response:
            raise RemoteTreeException(response["error"])

        logger.debug(
            "Receive JSON-RPC response ---\n" +
            json.dumps(response["result"], indent=2, ensure_ascii=False)
        )

        return response["result"]

    def _close(self) -> None:
        if self._session:
            del self._session
            self._session = None

    def get_trie_nodes(self) -> NoReturn:
        raise RemoteTreeException(
            "This method is not available for RemoteTree."
        )

    def installed_dictionary_version(self) -> str:
        return self.json_request(
            method="jageocoder.installed_dictionary_version",
            params={},
        )

    def installed_dictionary_readme(self) -> str:
        return self.json_request(
            method="jageocoder.installed_dictionary_readme",
            params={},
        )

    def search_by_trie(
            self, *args, **kwargs
    ) -> NoReturn:
        raise RemoteTreeException(
            "This method is not available for RemoteTree."
        )

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
        self.address_nodes.update_server_signature()
        rpc_result = self.json_request(
            method="jageocoder.searchNode",
            params={"query": query, "config": self.config},
        )
        results = []
        for r in rpc_result:
            result = Result.from_dict(r)
            result.node = self.get_node_by_id(r["node"]["id"])
            results.append(result)

        return results

    def create_note_index_table(self) -> None:
        """
        Collect notes from all address elements and create
        search table with index.
        """
        raise RemoteTreeException(
            "Cannot create index on RemoteTree."
        )

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
        self.address_nodes.update_server_signature()
        rpc_result = self.json_request(
            method="jageocoder.reverse",
            params={
                "x": x,
                "y": y,
                "level": level or AddressLevel.AZA,
            },
        )
        results = []
        for r in rpc_result:
            if not as_dict:
                r["candidate"] = self.get_node_by_id(r["candidate"]["id"])

            results.append(r)

        return results

    def search_by_machiaza_id(self, id: str) -> List[AddressNode]:
        self.address_nodes.update_server_signature()
        return super().search_by_machiaza_id(id)

    def search_by_postcode(self, code: str) -> List[AddressNode]:
        self.address_nodes.update_server_signature()
        return super().search_by_postcode(code)

    def search_by_prefcode(self, code: str) -> List[AddressNode]:
        self.address_nodes.update_server_signature()
        return super().search_by_prefcode(code)

    def search_by_citycode(self, code: str) -> List[AddressNode]:
        self.address_nodes.update_server_signature()
        return super().search_by_citycode(code)
