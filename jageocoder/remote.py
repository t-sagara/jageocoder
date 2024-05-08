from functools import lru_cache
import json
import os
import requests
from typing import Any, List, Optional, Union
import uuid

from jageocoder.address import AddressLevel
from jageocoder.exceptions import RemoteTreeException
from jageocoder.node import AddressNode
from jageocoder.result import Result
from jageocoder.tree import LRU


_session = None


def _json_request(
        url: str,
        method: str,
        params: object,
) -> Any:
    global _session
    payload = {
        "jsonrpc": "2.0",
        "method": method,
        "params": params,
        "id": str(uuid.uuid4()),
    }
    if _session is None:
        _session = requests.Session()

    response = _session.post(
        url=url,
        data=json.dumps(payload),
        headers={"Content-Type": "application/json"}
    ).json()

    if "error" in response:
        raise RemoteTreeException(response["error"])

    return response["result"]


class RemoteDataset(object):

    def __init__(self, url: str) -> None:
        self.url = url
        self.records = {}
        self._map = {}

    def load_record(self, id: int) -> None:
        rpc_result = _json_request(
            url=self.url,
            method="dataset.get",
            params={"id": id},
        )
        self._map[rpc_result["id"]] = rpc_result
        return rpc_result

    def get(self, id: int) -> dict:
        if id in self._map:
            return self._map[id]

        return self.load_record(id=id)


class RemoteNodeTable(object):

    def __init__(self, url: str) -> None:
        self.url = url
        self.datasets = RemoteDataset(url=url)
        self.cache = LRU()
        self.server_signature = None

    def update_server_signature(self) -> str:
        """
        Update the remote server's signature.

        Note
        ----
        - This method must be called before any processing
            that requires dictionary consistency to ensure
            the server has not been restarted during processing.
        """
        server_signature = _json_request(
            url=self.url,
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
        Get the record at the specified position
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

        rpc_result = _json_request(
            url=self.url,
            method="node.get_record",
            params={"pos": pos, "server": self.server_signature},
        )
        node = AddressNode(**rpc_result)
        node.table = self
        self.cache[pos] = node
        return node


class RemoteTree(object):
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
        self.url = url
        self.debug = debug
        self.address_nodes = RemoteNodeTable(url)
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
            The area can be specified by the list of name of the node
            (such as prefecture name or city name), or JIS code.

        - auto_redirect: bool (default = True)
            When this option is set and the retrieved node has a
            new address recorded in the "ref" attribute,
            the new address is retrieved automatically.
        """
        for k, v in kwargs.items():
            self.config[k] = v

    def get_config(
            self,
            keys: Union[str, List[str], None] = None
    ) -> dict:
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
        """
        if keys is None:
            return self.config

        if isinstance(keys, str):
            return self.config.get(keys)

        results = {}
        for key in keys:
            if key in self.config:
                results[key] = self.config[key]

        return results

    def _close(self) -> None:
        if _session:
            del _session
            _session = None

    def get_node_by_id(self, node_id: int) -> AddressNode:
        """
        Get the full node information by its id.

        Parameters
        ----------
        node_id: int
            The target node id.

        Return
        ------
        AddressNode
        """
        return self.address_nodes.get_record(node_id)

    def installed_dictionary_version(self) -> str:
        return _json_request(
            url=self.url,
            method="jageocoder.installed_dictionary_version",
            params={},
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
        rpc_result = _json_request(
            url=self.url,
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
        rpc_result = _json_request(
            url=self.url,
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
