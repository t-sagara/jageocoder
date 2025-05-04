from __future__ import annotations
import json
from logging import getLogger
import os
import re
from typing import Any, List, NoReturn, Optional
import uuid

import requests

from jageocoder.address import AddressLevel
from jageocoder.exceptions import RemoteTreeException
from jageocoder.node import AddressNode
from jageocoder.result import Result
from jageocoder.tree import AddressTree, LRU


logger = getLogger(__name__)


class RemoteDataset(object):

    def __init__(self, tree: RemoteTree) -> None:
        self.tree = tree
        self.records = {}
        self._map = None

    def load_record(self, id: int) -> None:
        rpc_result = self.tree.json_request(
            method="dataset.get",
            params={"id": id},
        )
        if self._map is None:
            self._map = {}

        self._map[rpc_result["id"]] = rpc_result
        return rpc_result

    def load_records(self) -> None:
        rpc_result = self.tree.json_request(
            method="dataset.get_all",
            params=[],
        )
        self._map = rpc_result
        return rpc_result

    def get(self, id: int) -> dict:
        if self._map is None:
            try:
                self.load_records()
            except RemoteTreeException:
                self._map = {}

        if id in self._map:
            return self._map[id]

        try:
            dataset = self.load_record(id)
            self._map[id] = dataset
            return dataset
        except RemoteTreeException:
            pass

        raise KeyError(f"'{id}' is not in the dataset keys.")

    def get_all(self) -> dict:
        if self._map is None:
            self.load_records()

        return self._map


class RemoteNodeTable(object):

    def __init__(self, tree: RemoteTree) -> None:
        self.tree = tree
        self.datasets = RemoteDataset(tree=tree)
        self.cache = LRU()
        self.server_signature = None
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
            self.server_signature = server_signature

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
        node.table = self
        self.cache[pos] = node
        return node

    def search_records_on(
            self,
            attr: str,
            value: str,
            funcname: str = "get") -> list:
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
        List[Record]
            List of records.

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
            node.table = self
            nodes.append(node)

        return nodes

    def search_ids_on(
        self,
        attr: str,
        value: str,
    ) -> list:
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
        List[Record]
            List of records.
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
        self._session = None
        self.url = url
        self.debug = debug
        self.address_nodes = RemoteNodeTable(tree=self)
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

    def set_config(
        self,
        **kwargs
    ) -> None:
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
            The area can be specified by the list of JIS code of the node.
            Note: Can't specify by node names when using remote server, currently.

        - auto_redirect: bool (default = True)
            When this option is set and the retrieved node has a
            new address recorded in the "ref" attribute,
            the new address is retrieved automatically.
        """
        for k, v in kwargs.items():
            self.validate_config(key=k, value=v)
            self.config[k] = v

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
        [[[11460207:東京都(139.69178,35.68963)1(lasdec:130001/jisx0401:13)]>[12063502:多摩市(139.446366,35.636959)3(jisx0402:13224)]>[12065383:落合(139.427097,35.624877)5(None)]>[12065384:一丁目(139.427097,35.624877)6(None)]>[12065390:15番地(139.428969,35.625779)7(None)], '多摩市落合1-15-']]
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
