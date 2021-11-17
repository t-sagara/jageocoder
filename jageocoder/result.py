import json
from logging import getLogger
from typing import NoReturn, Optional, Union

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
        The matched substringof the query.
    """

    def __init__(self,
                 node: Optional[AddressNode] = None,
                 matched: str = ''):
        self.node = node
        self.matched = matched

    def set(self, node: AddressNode,
            matched: str) -> 'Result':
        """
        Set node and matched string.
        """
        self.node = node
        self.matched = matched
        return self

    def get_node(self) -> AddressNode:
        """
        Get the node part of the result.

        Return
        ------
        AddressNode:
            The matched node.
        """
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

    def __getitem__(self, pos) -> Union[AddressNode, str]:
        if pos == 0:
            return self.node
        elif pos == 1:
            return self.matched

        raise IndexError()

    def __setitem__(self, pos, val: Union[AddressNode, str]) -> NoReturn:
        if pos == 0 and isinstance(val, AddressNode):
            self.node = val
        elif pos == 1 and isinstance(val, str):
            self.matched = val

        raise RuntimeError()

    def to_dict(self) -> dict:
        return {"node": self.node.as_dict(), "matched": self.matched}

    def __repr__(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
