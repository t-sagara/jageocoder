from __future__ import annotations
import json
from logging import getLogger
from typing import Optional, Union, TYPE_CHECKING

from .exceptions import JageocoderError

if TYPE_CHECKING:
    from jageocoder.node import AddressNode

logger = getLogger(__name__)


class Result(object):
    """
    Representing the result of searchNode().

    Attributes
    ----------
    node: AddressNode
        The node matched the query.
    matched: str
        The matched substring of the query.
    nchars: int
        The number of matched characters.
        It is used only for recursive search.
    """

    def __init__(
        self,
        node: Optional[AddressNode] = None,
        matched: str = '',
        nchars: int = 0
    ):
        self.node = node
        self.matched = matched
        self.nchars = nchars

    def set(
        self,
        node: AddressNode,
        matched: str,
        nchars: int = 0
    ) -> Result:
        """
        Set node and matched string.
        """
        self.node = node
        self.matched = matched
        self.nchars = nchars or len(matched)
        return self

    def get_node(self) -> AddressNode:
        """
        Get the node part of the result.

        Return
        ------
        AddressNode:
            The matched node.
        """
        if self.node is None:
            raise JageocoderError(
                "The result does not contain node information.")

        return self.node

    def get_matched_string(self) -> str:
        """
        Get the matched string part of the result.

        Return
        ------
        str:
            The matched substring.
        """
        return self.matched

    def get_matched_nchars(self) -> int:
        """
        Get the the number of matched characters.

        Return
        ------
        int
            Number of characters in the matched substring.
        """
        return self.nchars

    def __getitem__(
        self,
        pos
    ) -> Union[AddressNode, str, int]:
        if pos == 0:
            return self.get_node()
        elif pos == 1:
            return self.matched
        elif pos == 2:
            return self.nchars

        raise IndexError()

    def __setitem__(
        self,
        pos,
        val: Union[AddressNode, str]
    ) -> None:
        from jageocoder.node import AddressNode
        if pos == 0 and isinstance(val, AddressNode):
            self.node = val
        elif pos == 1 and isinstance(val, str):
            self.matched = val
        elif pos == 2 and isinstance(val, int):
            self.nchars = val

        raise RuntimeError()

    def as_dict(self) -> dict:
        """
        Convert Result object to dict type for display.

        Return
        ------
        dict
            A dict object containing the following elements;

            "node"
                AddressNode object converted to dict type.

            "matched"
                The substring matching the query.
        """
        return {
            "node": self.get_node().to_json(),
            "matched": self.matched,
        }

    @classmethod
    def from_dict(cls, jsonable: dict):
        from jageocoder.node import AddressNode
        return Result(
            node=AddressNode.from_dict(jsonable["node"]),
            matched=jsonable["matched"],
        )

    def as_geojson(self) -> dict:
        """
        Convert Result to GeoJSON dict type for display.

        Return
        ------
        dict
            A GeoJSON dict object containing the following elements;

            "type"
                Always "Feature".
            "geometry"
                A point type geometry containing latitude and longitude.
            "properties"
                Include in "matched" the substring that matched the query, in addition to the attributes of the node.
        """
        geojson = self.get_node().as_geojson()
        geojson['properties']['matched'] = self.matched
        return geojson

    def __repr__(self) -> str:
        return json.dumps(self.as_dict(), ensure_ascii=False)
