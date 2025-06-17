from __future__ import annotations
from collections.abc import Iterator
import copy
from functools import lru_cache
import json
import logging
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Set, Tuple, Optional, Sequence, Union, TYPE_CHECKING

import PortableTab

from .address import AddressLevel
from .dataset import Dataset
from .exceptions import AddressNodeError
from .itaiji import Converter
from .result import Result
from .strlib import strlib

if TYPE_CHECKING:
    from .tree import AddressTree

logger = logging.getLogger(__name__)
default_itaiji_converter = Converter()  # With default settings


class AddressNodeTable(PortableTab.BaseTable):
    """
    The address node table.
    """

    __tablename__ = "address_node"
    __schema__ = """
        struct AddressNode {
            id @0 :UInt32;
            name @1 :Text;
            nameIndex @2 :Text;
            x @3 :Float32;
            y @4 :Float32;
            level @5 :Int8;
            priority @6 :Int8;
            note @7 :Text;
            parentId @8 :UInt32;
            siblingId @9 :UInt32;
        }
        """
    __record_type__ = "AddressNode"

    def __init__(self, db_dir: os.PathLike) -> None:
        db_path = Path(db_dir)
        super().__init__(db_dir=db_path)
        self.datasets = Dataset(db_dir=db_path)

    @lru_cache(maxsize=1024)
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
        capnp_record = super().get_record(pos=pos)
        node = AddressNode.from_record(capnp_record)
        return node

    def search_ids_on(
        self,
        attr: str,
        value: str,
    ) -> list:
        """
        Search id list from the table on the specified attribute.

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
        trie = self.open_trie_on(attr)
        positions = trie.get(value, [])
        return [p[0] for p in positions]

    def create_indexes(self) -> None:
        """
        Create TRIE index on "name" and "note" columns.
        """
        def _split_note(note):
            notes = []
            for attr in re.split(r'(?<!\\)/', note):
                try:
                    k, v = re.split(r'(?<!\\):', attr, 1)
                except ValueError:
                    k, v = '', attr

                k = re.sub(r'\\([:/])', r'\g<1>', k)
                v = re.sub(r'\\([:/])', r'\g<1>', v)
                if k not in ('ref', 'geoshape_city_id'):
                    # Do not include these attributes in the search index.
                    notes.append(attr)

            return notes

        self.create_trie_on(
            attr="nameIndex",
            filter_func=lambda r: r.level <= AddressLevel.AZA
        )
        self.create_trie_on(
            attr="note",
            key_func=_split_note,
            filter_func=lambda r: r.level <= AddressLevel.AZA
        )


class AddressNode(object):
    """
    The address node stored in 'address_node' table.

    Parameters
    ----------
    id : int
        The key identifier that is automatically sequentially numbered.
    name : str
        The name of the address element, such as '東京都' or '新宿区'
    x : float
        X-coordinate value. (Longitude)
    y : float
        Y-coordinate value. (Latitude)
    level : int
        The level of the address element.
        The meaning of each value is as follows.
    priority : int
        Priority assigned to each source of data.
        Smaller value indicates higher priority.
    note : string
        Note or comment.
    parent_id : int
        The id of the parent node.
    sibling_id : int
        The id of the next sibling node.
    tree: Optional[AddressTree]
        The tree which contains this node.

    Attributes
    ----------
    name_index : str
        The standardized string for indexing created from its name.
    """
    ROOT_NODE_ID = 0
    NO_COORDINATE_VALUE = 999.9
    NONAME = "."  # Must be smaller than numbers.

    def __init__(
            self,
            id: int = 0,
            name: str = "",
            name_index: str = "",
            x: float = NO_COORDINATE_VALUE,
            y: float = NO_COORDINATE_VALUE,
            level: int = 0,
            priority: int = 0,
            note: str = "",
            parent_id: int = 0,
            sibling_id: int = 0,
            tree: Optional[AddressTree] = None,
    ) -> None:
        """
        The initializer of the node.

        In addition to the initialization of the record,
        the name_index is also created.
        """
        # Set basic attributes
        self.id: int = id
        self.name: str = name
        self.name_index: str = name_index
        self.x: float = x
        self.y: float = y
        self.level: int = level
        self.priority: int = priority
        self.note: str = note
        self.parent_id: int = parent_id
        self.sibling_id: int = sibling_id
        self.tree: Optional[AddressTree] = tree

        # For indexing
        if self.name_index is None:
            self.name_index = default_itaiji_converter.standardize(self.name)

    def get_tree(self) -> AddressTree:
        if self.tree is None:
            raise AddressNodeError("The node has no tree information.")

        return self.tree

    def has_valid_coordinate_values(self) -> bool:
        """
        Check if it has valid coordinate values.

        Returns
        -------
        bool
            True if x and y are both valid coordinate values.
        """
        return self.x >= -180.0 and self.x <= 180.0 and \
            self.y >= -90.0 and self.y <= 90.0

    def get_name(self, alt: Optional[str] = ''):
        """
        Name of node.

        Parameters
        ----------
        alt: str, optional
            String to be used when the node name is empty.
        """
        if self.name == self.NONAME:
            return alt

        return self.name

    @property
    def dataset(self):
        """
        Get dataset record.
        """
        datasets = self.get_tree().datasets
        if datasets is None:
            raise AddressNodeError("The tree has no datasets information")
        elif self.priority not in datasets:
            raise AddressNodeError(
                f"The tree has no dataset for id={self.priority}")

        return datasets[self.priority]

    @property
    def levelname(self) -> str:
        """
        Get level by name.
        """
        return AddressLevel.levelname(self.level)

    @classmethod
    def from_record(cls, record) -> AddressNode:
        """
        Convert from a record of AddressNodeTable to an AddressNode object.

        Parameters
        ----------
        record: CapnpRecord
            A record stored in PortableTab's table.

        Returns
        -------
        AddressNode
        """
        return AddressNode(
            id=record.id,
            name=record.name,
            name_index=record.nameIndex,
            x=record.x,
            y=record.y,
            level=record.level,
            priority=record.priority,
            note=record.note,
            parent_id=record.parentId,
            sibling_id=record.siblingId,
        )

    def to_record(self):
        """
        Convert from the AddressNode object to an object of
        dict that can be registered to the AddressNodeTable table.

        Returns
        -------
        dict
        """
        x = float(self.x or self.NO_COORDINATE_VALUE)
        y = float(self.y or self.NO_COORDINATE_VALUE)

        return {
            "id": int(self.id),
            "name": str(self.name or ""),
            "nameIndex": str(self.name_index or ""),
            "x": x if x <= 180.0 and x >= -180.0 else self.NO_COORDINATE_VALUE,
            "y": y if y <= 90.0 and y >= -90.0 else self.NO_COORDINATE_VALUE,
            "level": int(self.level or 0),
            "priority": int(self.priority or 0),
            "note": str(self.note or ""),
            "parentId": int(self.parent_id or 0),
            "siblingId": int(self.sibling_id or 0),
        }

    @classmethod
    def root(cls) -> AddressNode:
        """
        Generate the root AddressNode object.
        """
        return AddressNode(
            id=cls.ROOT_NODE_ID,
            name="_root_",
            x=cls.NO_COORDINATE_VALUE,
            y=cls.NO_COORDINATE_VALUE,
            level=0,
            priority=0,
            note="",
            parent_id=cls.ROOT_NODE_ID,
            sibling_id=0,
        )

    def set_attributes(self, **kwargs):
        """
        Set attributes of the node by kwargs values.

        Parameters
        ----------
        kwargs: dict
            A dictionary with the name of the attribute to be changed
            as key and the new value as value.

        Note
        ----
        The 'name' attribute can't be modified.
        """
        self.x = float(kwargs.get('x', kwargs.get(
            'lon', self.NO_COORDINATE_VALUE)))
        self.y = float(kwargs.get('y', kwargs.get(
            'lat', self.NO_COORDINATE_VALUE)))
        self.level = int(kwargs.get('level', -1))
        self.priority = int(kwargs.get('priority', 99))
        self.note = str(kwargs.get('note', ""))

    @property
    def parent(self) -> Optional[AddressNode]:
        """
        Get the parent node of the node.

        Return
        ------
        AddressNode
            The parent object.
            Return None when the parent node is the root node.
        """
        return self.get_parent()

    def get_parent(self) -> Optional[AddressNode]:
        """
        Get the parent node.

        Returns
        -------
        AddressNode
            The parent object.

        Notes
        -----
        - Returns None if the current node is directly under the root node.
        """
        if self.parent_id == self.__class__.ROOT_NODE_ID:
            return None
        elif self.parent_id < self.__class__.ROOT_NODE_ID:
            raise AddressNodeError(
                "Attempted to retrieve parent of node with invalid parent_id"
            )

        parent = self.get_tree().get_node_by_id(node_id=self.parent_id)
        return parent

    def get_child(self, target_name: str) -> Optional[AddressNode]:
        """
        Get a child node with the specified name.

        Parameters
        ----------
        target_name : str
            The name (or standardized name) of the target node.

        Returns
        -------
        Optional[AddressNode]
            If a node with the specified name is found, it is returned;
            Otherwise return None.
        """
        target_name_index = default_itaiji_converter.standardize(target_name)
        tree = self.get_tree()
        if target_name == target_name_index:
            targets = (target_name,)
        else:
            targets = (target_name, target_name_index,)

        for target in (targets):
            lb: int = self.id + 1  # lower bound
            ub: int = self.sibling_id  # upper bound
            cp: int = 0
            cp_node: Optional[AddressNode] = None
            lb_node: AddressNode = tree.get_node_by_id(node_id=lb)
            if lb_node.name_index == target:
                return lb_node

            while cp_node is None or \
                    ub > lb_node.sibling_id:
                cp = int((lb + ub) / 2)  # current position
                cp_node = tree.get_node_by_id(node_id=cp)
                if cp_node.parent_id != self.id:
                    while cp_node.parent_id != self.id:
                        cp = cp_node.parent_id
                        cp_node = tree.get_node_by_id(node_id=cp)

                    if cp == lb and cp_node.sibling_id < ub:
                        cp = cp_node.sibling_id
                        cp_node = tree.get_node_by_id(node_id=cp)

                if cp_node.name_index < target:
                    lb = cp
                    lb_node = tree.get_node_by_id(node_id=lb)
                elif cp_node.name_index == target:
                    break
                else:
                    ub = cp

            while cp < ub:
                cp_node = tree.get_node_by_id(node_id=cp)
                if cp_node.name_index == target:
                    return cp_node
                elif cp_node.name_index > target:
                    break

                cp += 1

        return None

    @property
    def children(self) -> List[AddressNode]:
        """
        Get child nodes of the node.

        Returns
        -------
        List[AddressNode]
            The list of the child nodes.

        """
        return self.get_children()

    def get_children(self) -> List[AddressNode]:
        """
        Get child nodes of the node.

        Returns
        -------
        List[AddressNode]
            The list of the child nodes.
        """
        return list(self.iter_children())

    def iter_children(self) -> Iterator[AddressNode]:
        """
        Iterate children of the node.

        Returns
        -------
        Iterator[AddressNode]
            An iterator object that returns a child node in sequence.
        """
        pos: int = self.id + 1
        tree = self.get_tree()
        while pos < self.sibling_id:
            node = tree.get_node_by_id(node_id=pos)
            if node.parent_id == self.id:
                yield node
                pos = node.sibling_id
            else:
                parent = tree.get_node_by_id(node_id=node.parent_id)
                pos = parent.sibling_id

    def get_notes(self) -> Tuple[Tuple[str, str]]:
        """
        Get list of key-value set from the note field.

        Returns
        -------
        Tuple[Tuple[str, str]]
            Tuple containing tuples consisting of keys and values.
        """
        notes = []
        for attr in re.split(r'(?<!\\)/', self.note):
            try:
                k, v = re.split(r'(?<!\\):', attr, 1)
            except ValueError:
                k, v = '', attr

            k = re.sub(r'\\([:/])', r'\g<1>', k)
            v = re.sub(r'\\([:/])', r'\g<1>', v)
            notes.append((k, v))

        return tuple(notes)

    def set_notes(self, notes: Sequence[Tuple[str, str]]) -> None:
        """
        Set the note field from the list of key-value set.

        Parameters
        ----------
        notes: ((str, str))
            List of key-value set (as tuples).
        """
        attrs = []
        for attr in notes:
            k = re.sub(r'[:/]', r'\\\g<0>', attr[0])
            v = re.sub(r'[:/]', r'\\\g<0>', attr[1])
            attrs.append(f'{k}:{v}')

        self.note = '/'.join(attrs)

    def add_note(self, key: str, value: str) -> None:
        """
        Add an attribute with key-value set to the note field.

        Parameters
        ----------
        key: str
            The key of the attribute to be added.
        value: str
            The value of the attribute to be added.
        """
        notes = list(self.get_notes())
        notes.append((key, value))
        self.set_notes(notes)

    def add_dummy_coordinates(self) -> AddressNode:
        """
        Add dummy coordinate values to the node.
        If the coordinates of the node are not specified,
        this method selects a child node with valid coordinates
        and temporarily duplicates it.

        Notes
        -----
        - The duplicated values are not registered in the database.
        """
        new_node = copy.copy(self)
        for child in self.iter_children():
            if child.has_valid_coordinate_values():
                new_node.x, new_node.y = child.x, child.y
                logger.debug((
                    "Node {}({}) has no coordinates. "
                    "Use the coordinates of the child {}({}) instead."
                ).format(
                    self.name, self.id, child.name, child.id))
                break

        return new_node

    def search_child_with_criteria(
        self,
        pattern: str,
        min_candidate: Optional[str] = None,
        gt_candidate: Optional[str] = None,
        max_level: Optional[int] = None,
    ) -> List[AddressNode]:
        """
        Search for children nodes that satisfy the specified conditions.

        Parameters
        ----------
        pattern: str
            The regular expression that the child node's name must match.
        min_candidate: str, optional
            The smallest string that satisfies the condition
            as the name of a child node.
        gt_candidate: str, optional
            The smallest string that exceeds the upper limit
            that satisfies the condition as the name of a child node.
        max_level: int, optional
            Maximum level of child nodes; unlimited if None.

        Returns
        -------
        List[AddressNode]
            A list of all child nodes that satisfy the specified condition.
        """
        logger.debug((
            "Called with self:'{}'({}), pattern:{}, min:'{}', gt:'{}', max_level: {}."
        ).format(
            self.name,
            self.id,
            pattern,
            min_candidate,
            gt_candidate,
            max_level,
        ))
        tree = self.get_tree()
        re_pattern = re.compile(pattern)
        address_node = tree.get_node_by_id(node_id=self.id)
        children = []

        if self.sibling_id == self.id + 1:  # No child
            logger.debug(
                "Returns an empty result because the node (self) "
                "has no child."
            )
            return []

        # Find the range of IDs of nodes that satisfy the condition
        lb: int = self.id + 1  # lower bound
        if min_candidate is None:
            next_pos = self.id
        else:
            # Use binary search
            ub: int = address_node.sibling_id  # upper bound
            cp: int = 0
            candidate: Optional[AddressNode] = None
            while candidate is None or \
                    ub > tree.get_node_by_id(node_id=lb).sibling_id:
                cp = int((lb + ub) / 2)  # current position
                candidate = tree.get_node_by_id(node_id=cp)
                if candidate.parent_id != self.id:
                    while candidate.parent_id != self.id:
                        cp = candidate.parent_id
                        candidate = tree.get_node_by_id(node_id=cp)

                    if cp == lb and candidate.sibling_id < ub:
                        cp = candidate.sibling_id
                        candidate = tree.get_node_by_id(node_id=cp)

                if candidate.name_index < min_candidate:
                    lb = cp
                else:
                    ub = cp

            next_pos = lb

        # Scan all records in the range
        while next_pos < address_node.sibling_id:
            candidate = tree.get_node_by_id(node_id=next_pos)

            if gt_candidate is not None and \
                    candidate.name_index >= gt_candidate:
                break

            if re_pattern.match(candidate.name_index) and \
                    (max_level is None or candidate.level <= max_level):
                if candidate.y > 90.0:
                    candidate = candidate.add_dummy_coordinates()

                children.append(candidate)

            next_pos = candidate.sibling_id

        logger.debug("Returns {} children.".format(len(children)))
        return children

    def search_recursive(
            self,
            index: str,
            processed_nodes: Set[int],
    ) -> List[Result]:
        """
        Search nodes recursively that match the specified address notation.

        Parameters
        ----------
        index : str
            The standardized address notation.
        processed_nodes: Set of the AddressNode's id
            List of node's id that have already been processed
            by TRIE search results.

        Return
        ------
        List[Result]
            List of Result objects containing relevant AddressNode.
        """
        tree = self.get_tree()
        l_optional_prefix = tree.converter.check_optional_prefixes(index)
        optional_prefix = index[0: l_optional_prefix]
        index = index[l_optional_prefix:]

        logger.debug((
            "Called with self:'{}'({}), index:{}, processed_nodes:{}".format(
                self.name,
                self.id,
                index,
                processed_nodes
            )))
        if processed_nodes is None:
            raise AddressNodeError(
                "AddressNode.search_recursive received None for processed_nodes."
            )

        if len(index) == 0:
            logger.debug((
                "Returns an empty result because it matched up "
                "to the last character."
            ))
            processed_nodes.add(self.id)
            logger.debug(f"{self.name}({self.id}) marked as processed")
            return [Result(self, "", 0)]

        if self.sibling_id == self.id + 1:
            logger.debug(f"{self.name}({self.id}) has no child.")
            candidates = self.check_redirect(index, processed_nodes)

            if len(candidates) == 0:
                candidates = [Result(self, "", 0)]

            return candidates

        max_level = None
        v = strlib.get_number(index)
        if v['i'] > 0:
            # If it starts with a number,
            # look for a node that matches the numeric part exactly.
            substr = str(v['n']) + r'\..*'
            min_candidate = str(v['n']) + '.'
            gt_candidate = str(v['n']) + '/'  # '/' is next char of '.'
        else:
            # If it starts with not a number,
            # look for a node with a maching first letter.
            substr = re.escape(index[0:1]) + r'.*'
            min_candidate = index[0:1]
            gt_candidate = chr(ord(index[0:1]) + 1)

        if '字' in optional_prefix:
            max_level = AddressLevel.AZA

        filtered_children = self.search_child_with_criteria(
            pattern=substr,
            min_candidate=min_candidate,
            gt_candidate=gt_candidate,
            max_level=max_level,
        )

        # Check if the index begins with an extra character of
        # the current node.
        if len(filtered_children) == 0 and \
                index[0] in tree.converter.extra_characters:
            logger.debug((
                "Remove the leading extra character '{}' and "
                "search candidates again.").format(index[0]))
            candidates = self.search_recursive(
                index=index[1:],
                processed_nodes=processed_nodes)
            if len(candidates) > 0:
                new_candidates = []
                for candidate in candidates:
                    if candidate.get_node().id == self.id:
                        new_candidates.append(candidate)
                        continue

                    new_candidate = Result(
                        candidate.node,
                        index[0] + candidate.matched,
                        l_optional_prefix + candidate.nchars)
                    new_candidates.append(new_candidate)

                new_candidates.append(Result(self, "", 0))
                return new_candidates

            return []

        if logger.isEnabledFor(logging.DEBUG):
            if len(filtered_children) == 0:
                msg = "No matched children. (#children:{})".format(
                    len(self.get_children()))
            else:
                msg = "Matched children are; {}".format(
                    ','.join([x.name for x in filtered_children]))

            logger.debug(msg)

        candidates = []
        for child in filtered_children:
            if child.id in processed_nodes:
                msg = "-> Skip {}({}) (already processed)."
                logger.debug(msg.format(child.name, child.id))
                continue

            logger.debug("-> comparing; {}".format(child.name))
            new_candidates = child._get_candidates(
                tree=tree,
                index=index,
                optional_prefix=optional_prefix,
                processed_nodes=processed_nodes)

            if len(new_candidates) > 0:
                candidates += new_candidates
                candidates.append(Result(self, "", 0))

        # Processes the region's own rules.
        parent_node = self.get_parent()
        if self.level == AddressLevel.WARD and parent_node and parent_node.name == '京都市':
            # Street name (通り名) support in Kyoto City
            # If a matching part of the search string is found in the
            # child nodes, the part before the name is skipped
            # as a street name.
            for child in self.get_children():
                pos = index.rfind(child.name_index)
                if pos <= 0:
                    continue

                offset = pos + len(child.name_index)
                rest_index = index[offset:]
                logger.debug(
                    "child:{} match {} chars".format(child, offset))
                processed_nodes.add(child.id)
                logger.debug(f"{child.name}({child.id}) marked as processed")
                new_candidates = child.search_recursive(
                    index=rest_index,
                    processed_nodes=processed_nodes)
                for cand in new_candidates:
                    candidates.append(Result(
                        node=cand.get_node(),
                        matched=optional_prefix +
                        index[0: offset] + cand.get_matched_string(),
                        nchars=l_optional_prefix + len(child.name_index) +
                        len(cand.get_matched_string()))
                    )

                if len(new_candidates) > 0:
                    candidates.append(Result(self, "", 0))

        # Search for nodes with possible address changes.
        candidates += self.check_redirect(index, processed_nodes)

        # Search for subnodes with queries excludes Aza-name candidates.
        omissible_index = None
        aza_skip = tree.get_config('aza_skip')
        if len(candidates) == 0 or \
                len(index) - len(candidates[0].matched) > 2:
            logger.debug((
                "Try to skip over the omissible Aza-names and "
                "search for matching nodes since no candidates found."
            ))
            if aza_skip is False:   # Skip = off
                omissible_index = ""
            elif aza_skip is None:  # Skip = auto
                omissible_index = self.get_omissible_index(
                    index=index,
                    processed_nodes=processed_nodes,
                    strict=True)
            elif aza_skip is True:  # Skip = on
                omissible_index = self.get_omissible_index(
                    index=index,
                    processed_nodes=processed_nodes,
                    strict=False)

        if omissible_index is None:
            pass  # has candidate, or aza_skip is prohibitted
        elif omissible_index == "":
            logger.debug("No omissible Aza-names are found.")
        else:
            azalen = tree.converter.optional_aza_len(index, 0)
            if azalen > len(omissible_index):
                azalen = 0

            if azalen > 0:
                msg = '"{}" in index "{}" is omissible.'
                logger.debug(msg.format(index[:azalen], index))
                # Note: Disable 'aza_skip' here not to perform
                # repeated skip processing.
                tree.set_config(aza_skip=False)
                sub_candidates = self.search_recursive(
                    index=index[azalen:],
                    processed_nodes=processed_nodes)
                tree.set_config(aza_skip=aza_skip)
                if sub_candidates[0].matched != '':
                    added = 0
                    for cand in sub_candidates:
                        node = cand.get_node()
                        if node.level < AddressLevel.BLOCK and \
                                node.name_index not in \
                                tree.converter.chiban_heads:
                            logger.debug("{} is ignored".format(
                                node.name))
                            continue

                        candidates.append(Result(
                            node,
                            optional_prefix +
                            index[0:azalen] + cand.get_matched_string(),
                            l_optional_prefix + cand.get_matched_nchars()))
                        added += 1

                    if added > 0:
                        candidates.append(Result(self, "", 0))

        if False and len(candidates) == 0:
            # Search common names
            for k, v in self.get_notes():
                if k != "cn":
                    continue

                assert (self.name == self.NONAME)
                parent = self.parent
                for cn in v.split('|'):
                    logger.debug(f"Search by common name '{cn}'.")
                    new_index = cn + index
                    new_candidates = parent.search_recursive(
                        index=new_index,
                        processed_nodes=processed_nodes
                    )
                    for candidate in new_candidates:
                        if len(candidate.matched) > len(cn):
                            matched = candidate.matched[len(cn):]
                            logger.debug("Added '{}'({}) as '{}'.".format(
                                candidate.node.name,
                                candidate.matched,
                                matched
                            ))
                            candidate.matched = matched
                            candidate.nchars = len(matched)
                            candidates.append(candidate)

        if len(candidates) == 0:
            candidates = [Result(self, '', 0)]

        logger.debug((
            "returned '{}', self:'{}'({}), index:{}.").format(
                candidates,
                self.name,
                self.id,
                index
        ))
        return candidates

    def check_redirect(
        self,
        index: str,
        processed_nodes: Set[int]
    ) -> List[Result]:
        tree = self.get_tree()
        auto_redirect = tree.get_config('auto_redirect')
        require_coordinates = tree.get_config('require_coordinates')
        if auto_redirect is False:
            return []

        candidates = []
        # Search redirect nodes
        for k, v in self.get_notes():
            if k != "ref":
                continue

            for ref in v.split('|'):
                logger.debug(
                    f"Redirect '{self.get_fullname()}' to '{ref}'"
                )
                processed_nodes.add(self.id)
                logger.debug(
                    f"{self.name}({self.id}) marked as processed")
                tree.set_config(auto_redirect=False, require_coordinates=False)
                redirect_results = tree.searchNode(ref)
                tree.set_config(
                    auto_redirect=auto_redirect,
                    require_coordinates=require_coordinates
                )
                for result in redirect_results:
                    node = result.get_node()
                    if node.id in processed_nodes:
                        continue

                    for result in node.search_recursive(index, processed_nodes):
                        if len(result.matched) > 0:
                            candidates.append(result)

        return candidates

    def _get_candidates(
            self,
            tree: AddressTree,
            index: str,
            optional_prefix: str,
            processed_nodes: Set[int]) -> List[AddressNode]:
        """
        Get candidates from the self node.

        Parameters
        ----------
        tree: AddressTree
            The tree containing this node.
        index: str
            Standardized query string. Numeric characters are kept as
            original notation.
        optional_prefix: str
            The option string that preceded the string passed by index.

        Returns
        -------
        List[AddressNode]
            The list of candidates.
            Each element of the array has the matched AddressNode
            as the first element and the matched string
            as the second element.
        """

        match_len = tree.converter.match_len(index, self.name_index)
        if match_len == 0:
            l_optional_postfix = tree.converter.check_optional_postfixes(
                self.name_index, self.level)
            if l_optional_postfix > 0:
                # In case the index string of the self node with optional
                # postfixes removed is completely included in the beginning
                # of the search string.
                # ex. index='2.-8.', self.name_index='2.番' ('番' is a postfix)
                optional_postfix = self.name_index[-l_optional_postfix:]
                alt_index = self.name_index[0: -l_optional_postfix]
                logger.debug(
                    "self:{} has optional postfix {}".format(
                        self, optional_postfix))
                match_len = tree.converter.match_len(
                    index, alt_index, removed_postfix=optional_postfix)

                if tree.converter.check_trailing_string(
                        index[match_len:], self.level):
                    match_len = 0
                elif match_len < len(index) and index[match_len] in '-ノ':
                    match_len += 1

        if match_len == 0 and self.name_index.endswith('.条'):
            # Support for Sapporo City and other cities that use
            # "北3西1" instead of "北3条西１丁目".
            alt_index = self.name_index.replace('条', '', 1)
            logger.debug("self:{} ends with '.条'".format(self))
            match_len = tree.converter.match_len(index, alt_index)

        if match_len == 0:
            logger.debug("{} doesn't match".format(self.name))
            return []

        candidates = []
        offset = match_len
        rest_index = index[offset:]
        l_optional_prefix = len(optional_prefix)
        logger.debug("self:{} match {} chars".format(self, offset))
        # logger.debug(f"{self.name}({self.id}) marked as processed")
        for cand in self.search_recursive(
                index=rest_index,
                processed_nodes=processed_nodes):
            candidates.append(Result(
                cand.node,
                optional_prefix + index[0:match_len] + cand.matched,
                l_optional_prefix + match_len + cand.nchars))

        return candidates

    def get_omissible_index(
            self,
            index: str,
            processed_nodes: Set[int],
            strict: bool = False) -> str:
        """
        Obtains an optional leading substring from the search string index.

        Parameters
        ----------
        index: str
            Target string.
        processed_nodes: List of AddressNode
            List of nodes that have already been processed
            by TRIE search results.
        strict: bool
            If true, check the omission more strict.

        Returns
        -------
        str
            The optional leading substring.
            If not omissible, an empty string is returned.

        Notes
        -----
        - Retrieve the lower address elements of this node
          that have start_count_type is 1 from the aza_master.
        - If the name of the element is contained in the index,
          the substring before the name is returned.
        - This method can only be called from nodes in LocalTree.
        """
        from .local_tree import LocalTree
        if self.level < AddressLevel.CITY or \
                self.level > AddressLevel.AZA:
            return ""

        _tree = self.get_tree()
        if not isinstance(_tree, LocalTree):
            raise AddressNodeError(
                "'get_ommisible_index' can only be called from nodes in LocalTree.")
        tree: LocalTree = _tree

        for id in processed_nodes or []:
            node = tree.get_node_by_id(node_id=id)
            if node.parent_id == self.parent_id and \
                    node.name_index != self.name_index:
                logger.debug((
                    "Can't skip substring after '{}', "
                    "a sibling node {} had been selected").format(
                        self.name, node.name))
                return ""

            elif node.parent_id == self.id:
                logger.debug((
                    "Can't skip substring after '{}', "
                    "a self node {} had been selected").format(
                        self.name, node.name))
                return ""

        if self.level < AddressLevel.OAZA:
            target_prefix = self.get_city_jiscode()
        else:
            target_prefix = self.get_aza_code().rstrip('0')

        if target_prefix == "":
            logger.debug((
                "Consider '{}' is omissible, "
                "since the node {} doesn't have city/aza code.").format(
                    index, self.name))
            return index

        # Search sub-aza-records using TRIE index on "code"
        logger.debug(
            "Scanning '{}' in sub aza-records of '{}'".format(
                index, self.name))

        aza_records = tree.aza_masters.search_records_on(
            attr="code",
            value=target_prefix,
            funcname="keys"
        )
        if not strict:
            # Consider omittable except for those parts that cannot
            # be omitted by Aza-master.
            omissible_index = index
            for aza_record in aza_records:
                if not strict and (aza_record.azaClass == 3 and
                                   aza_record.startCountType == 1) or \
                        aza_record.azaClass == 1:

                    names = json.loads(aza_record.names)
                    # logger.debug(
                    #     "  -> '{}' is not omissible.".format(names[-1][1]))
                    name = tree.converter.standardize(names[-1][1])
                    pos = omissible_index.find(name)
                    if pos >= 0:
                        logger.debug(
                            "Can't omit substring '{}' from '{}' in {}".format(
                                name, names[-1][1], omissible_index))
                        omissible_index = omissible_index[0:pos]

                        if pos == 0:
                            break

        else:  # strict mode
            # Consider omittable only those portions that can be omitted
            # with by Aza-master.
            omissible_index = ""
            for aza_record in aza_records:
                if aza_record.startCountType == 1:
                    names = json.loads(aza_record.names)
                    name = tree.converter.standardize(names[-1][1])
                    if name == self.name_index:
                        logger.debug((
                            "Can omit string after '{}' "
                            "since it's startCountType=1"
                        ).format(self.name))
                        omissible_index = index
                        break

                if aza_record.startCountType == 2:
                    names = json.loads(aza_record.names)
                    name = tree.converter.standardize(names[-1][1])
                    pos = index.find(name)
                    if pos > len(omissible_index):
                        logger.debug(
                            "Can omit substring '{}' from '{}' in {}".format(
                                name, names[-1][1], index))
                        omissible_index = index[0:pos]

                    if pos == len(index):
                        break

        logger.debug("  -> omissible '{}'".format(omissible_index))
        return omissible_index

    def get_omissible_children(self) -> List[AddressNode]:
        """
        Create a list of omissible child nodes refer to Aza-master.

        Returns
        -------
        List[AddressNode]
            List of omissible child nodes.

        Notes
        -----
        - This method can only be called from nodes in LocalTree.
        """
        from .local_tree import LocalTree
        if self.level < AddressLevel.CITY or \
                self.level > AddressLevel.AZA:
            return []

        _tree = self.get_tree()
        if not isinstance(_tree, LocalTree):
            raise AddressNodeError(
                "'get_ommisible_children' can only be called from nodes in LocalTree.")
        tree: LocalTree = _tree

        if self.level < AddressLevel.OAZA:
            target_prefix = self.get_city_jiscode()
        else:
            target_prefix = self.get_aza_code().rstrip('0')

        if target_prefix == "":  # Skip unknown OAZA
            return []

        candidates = {}
        for child in self.children:
            if child.level > AddressLevel.AZA:
                continue

            candidates[child.name_index] = child

        # Search sub-aza-records using TRIE index on "code"
        logger.debug("Scanning aza-records")
        aza_records = tree.aza_masters.search_records_on(
            attr="code",
            value=target_prefix,
            funcname="keys"
        )
        for aza_record in aza_records:
            if aza_record.startCountType == 1:  # 起番
                names = json.loads(aza_record.names)
                for e in names:
                    level = e[0]
                    if level < AddressLevel.OAZA:
                        continue

                    name = tree.converter.standardize(e[1])
                    if name in candidates:
                        logger.debug("  -> '{}' is not omissible.".format(
                            names[-1][1]))
                        del candidates[name]

        return list(candidates.values())

    def as_dict(self):
        """
        Return the dict notation of the node.
        """
        return {
            "id": self.id,
            "name": self.get_name(),
            "x": self.x,
            "y": self.y,
            "level": self.level,
            "priority": self.priority,
            "note": self.note,
            "fullname": self.get_fullname(),
        }

    @classmethod
    def from_dict(cls, jsonable: dict):
        return AddressNode(
            id=jsonable["id"],
            name=jsonable["name"],
            x=jsonable["x"],
            y=jsonable["y"],
            level=jsonable["level"],
            priority=jsonable["priority"],
            note=jsonable["note"],
            parent_id=jsonable.get("parent_id", -1),
            sibling_id=jsonable.get("sibling_id", -1),
        )

    def as_geojson(self):
        """
        Return the geojson notation of the node.
        """
        properties = self.as_dict()
        del properties["x"]
        del properties["y"]
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.x, self.y]
            },
            "properties": properties,
        }

    def to_json(self):
        """
        Convert node to JSONable dict for data transfer.

        Notes
        -----
        - Different from the 'as_dict' method, this method includes
            all attributes in the database, such as 'parent_id'.
        """
        return {
            "id": self.id,
            "name": self.name,
            "name_index": self.name_index,
            "x": self.x,
            "y": self.y,
            "level": self.level,
            "priority": self.priority,
            "note": self.note,
            "parent_id": self.parent_id,
            "sibling_id": self.sibling_id,
        }

    def get_fullname(
        self,
        delimiter: Optional[str] = None,
        alt: Optional[str] = '',
    ) -> Union[str, List[str]]:
        """
        Returns a complete address notation starting with the name of
        the prefecture.

        Parameters
        ----------
        delimiter: str, optional
            Specifies the delimiter character for the address element;
            If None is specified, returns a list of elements.
        alt: str, optional
            String to be used instead if the node name is empty.

        Returns
        -------
        str, List[str]
            If a delimiter is specified (including ""), returns a string
            consisting of the name of the address node concatenated
            with the delimiter.
            Otherwise, it returns a list of address node names.
        """
        names = []
        cur_node = self
        while cur_node is not None:
            names.insert(0, cur_node.get_name(alt))
            cur_node = cur_node.get_parent()

        if isinstance(delimiter, str):
            return delimiter.join(names)

        return names

    def get_parent_list(self) -> List[AddressNode]:
        """
        Returns a complete node list starting with the prefecture.
        """
        nodes = []
        cur_node = self
        while cur_node is not None:
            nodes.insert(0, cur_node)
            cur_node = cur_node.get_parent()

        return nodes

    def get_nodes_by_level(self) -> List[Optional[List[AddressNode]]]:
        """
        The method returns an array of this node and its upper nodes.
        The Nth node of the array contains the node corresponding
        to address level N.
        If there is no element corresponding to level N, None is stored.

        Example
        -------
        >>> import jageocoder
        >>> jageocoder.init()
        >>> node = jageocoder.searchNode('多摩市落合1-15')[0][0]
        >>> [str(x) for x in node.get_nodes_by_level()]
        ['None', "[{'id': ..., 'name': '東京都', 'x': 139.6..., 'y': 35.6..., 'level': 1, 'priority': 1, 'note': 'lasdec:130001/jisx0401:13', 'fullname': ['東京都']}]", 'None', "[{'id': ..., 'name': '多摩市', 'x': 139.4..., 'y': 35.6..., 'level': 3, 'priority': 1, 'note': 'geoshape_city_id:13224A1971/jisx0402:13224/postcode:2060000', 'fullname': ['東京都', '多摩市']}]", 'None', "[{'id': ..., 'name': '落合', 'x': 139.4..., 'y': 35.6..., 'level': 5, 'priority': 2, 'note': '', 'fullname': ['東京都', '多摩市', '落合']}]", "[{'id': ..., 'name': '一丁目', 'x': 139.4..., 'y': 35.6..., 'level': 6, 'priority': 2, 'note': 'aza_id:0010001/postcode:2060033', 'fullname': ['東京都', '多摩市', '落合', '一丁目']}]", "[{'id': ..., 'name': '15番地', 'x': 139.4..., 'y': 35.6..., 'level': 7, 'priority': 3, 'note': '', 'fullname': ['東京都', '多摩市', '落合', '一丁目', '15番地']}]"]
        """  # noqa: E501
        result: List[Optional[List[AddressNode]]] = [
            None for _ in range(self.level + 1)]
        cur_node = self
        while cur_node is not None:
            if result[cur_node.level] is None:
                result[cur_node.level] = [cur_node]
            else:
                result[cur_node.level].insert(0, cur_node)  # type: ignore

            cur_node = cur_node.get_parent()

        return result

    def __str__(self):
        return '[{}:{}({},{}){}({})]'.format(
            self.id, self.get_name(), self.x, self.y, self.level, str(self.note))

    def __repr__(self):
        return str(self.as_dict())

    def retrieve_upper_node(self, target_levels: List[int]):
        """
        Retrieves the node at the specified level from
        the this node or one of its upper nodes.
        """
        cur_node = self
        while cur_node is not None and \
                cur_node.level not in target_levels:
            cur_node = cur_node.get_parent()

        if cur_node is not None and cur_node.level in target_levels:
            return cur_node

        return None

    def get_pref_name(self) -> str:
        """
        Returns the name of prefecture that contains this node.
        """
        node = self.retrieve_upper_node([AddressLevel.PREF])
        if node is None:
            return ''

        return node.name

    def get_pref_jiscode(self) -> str:
        """
        Returns the jisx0401 code of the prefecture that
        contains this node.
        """
        node = self.retrieve_upper_node([AddressLevel.PREF])
        if node is None or node.note is None:
            return ''

        m = re.search(r'jisx0401:(\d{2})', node.note)
        if m:
            return m.group(1)

        return ''

    def get_pref_local_authority_code(self) -> str:
        """
        Returns the 地方公共団体コード of the prefecture that
        contains this node.
        """
        jisx0401 = self.get_pref_jiscode()
        if jisx0401 == '':
            return ''

        return self._local_authority_code(jisx0401 + '000')

    def get_city_name(self) -> str:
        """
        Returns the name of city that contains this node.
        """
        node = self.retrieve_upper_node([
            AddressLevel.CITY, AddressLevel.WARD])
        if node is None:
            return ''

        return node.name

    def get_city_jiscode(self) -> str:
        """
        Returns the jisx0402 code of the city that
        contains this node.
        """
        node = self.retrieve_upper_node([
            AddressLevel.CITY, AddressLevel.WARD])
        if node is None or node.note is None:
            return ''

        m = re.search(r'jisx0402:(\d{5})', node.note)
        if m:
            return m.group(1)

        return ''

    def get_city_local_authority_code(self) -> str:
        """
        Returns the 地方公共団体コード of the city that
        contains this node.
        """
        jisx0402 = self.get_city_jiscode()
        if jisx0402 == '':
            return ''

        return self._local_authority_code(jisx0402)

    def _local_authority_code(self, orig_code: str) -> str:
        """
        Returns the 6-digit code, adding a check digit to the JIS code.
        https://www.soumu.go.jp/main_content/000137948.pdf
        """
        if len(orig_code) != 5:
            raise RuntimeError('The original code must be a 5-digit string.')

        sum = int(orig_code[0]) * 6 + int(orig_code[1]) * 5 +\
            int(orig_code[2]) * 4 + int(orig_code[3]) * 3 +\
            int(orig_code[4]) * 2
        if sum < 11:
            checkdigit = str(11 - sum)
        else:
            remainder = sum % 11
            checkdigit = str(11 - remainder)[-1]

        return orig_code + checkdigit

    def get_aza_id(self) -> str:
        """
        Returns the AZA-id defined by JDA address-base-registry
        containing this node.
        """
        node = self
        while True:
            if node.note and 'aza_id' in node.note:
                m = re.search(r'aza_id:(\d{7})', node.note)
                if m:
                    return m.group(1)

            node = node.get_parent()
            if node is None:
                break

        return ''

    def get_machiaza_id(self) -> str:
        """
        Returns the MachiAza ID defined by JDA address-base-registry
        containing this node.

        Note
        ----
        - This method is an alias for 'get_aza_id'.
        """
        return self.get_aza_id()

    def get_aza_code(self) -> str:
        """
        Returns the 'AZA-code' concatinated with the city-code
        and the aza-id containing this node.
        """
        aza_id = self.get_aza_id()
        if aza_id != '':
            return self.get_city_jiscode() + aza_id

        return ''

    def get_aza_record(self) -> Dict[str, Any]:
        """
        Returns ABR's aza record corresponding to this node..

        Returns
        -------
        Record of AzaMaster
            A record object if exists. Otherwise None.
        """
        if self.level >= AddressLevel.OAZA:
            code = self.get_aza_code()
        elif self.level >= AddressLevel.CITY:
            code = self.get_city_jiscode()
        else:
            code = self.get_pref_jiscode()

        aza_record = self.get_tree().search_aza_records_by_codes(code)
        return aza_record

    def get_aza_names(
        self,
        tree: Optional[AddressTree] = None,
        levelname: Optional[bool] = False,
    ) -> Tuple[Tuple[Union[int, str], str, str, str, str]]:
        """
        Returns representation of Aza node containing this node.

        Parameters
        ----------
        levelname: bool, optional
            If true, Returns the address level by name, not by number.

        Returns
        -------
        list
            A list containing notations from the prefecture level
            to the Aza level in the following format:

            [AddressLevel, Kanji, Kana, English, code]
        """
        if tree is not None:
            logger.warning(
                "Deprecated: 'tree' parameter is passed but ignored in 'AddressNode:get_aza_names'.")

        aza_record = self.get_aza_record()
        if aza_record is not None:
            results = json.loads(aza_record["names"])  # type: ignore
            if levelname:
                for i in range(len(results)):
                    results[i][0] = AddressLevel.levelname(results[i][0])

            return results

        return tuple()

    def get_postcode(self) -> str:
        """
        Returns the 7digit postcode of the oaza that
        contains this node.
        """
        node = self
        while node is not None:
            if node.level <= AddressLevel.COUNTY:
                break

            if node.note and 'postcode' in node.note:
                m = re.search(r'postcode:(\d{7})', node.note)
                if m:
                    return m.group(1)

            node = node.get_parent()

        return ''

    def get_gsimap_link(self) -> str:
        """
        Returns the URL for GSI Map with parameters.
        ex. https://maps.gsi.go.jp/#13/35.713556/139.750385/
        """
        if self.level is None or self.x is None or self.y is None:
            return ''

        url = 'https://maps.gsi.go.jp/#{level:d}/{lat:.6f}/{lon:.6f}/'
        return url.format(
            level=9 + self.level,
            lat=self.y, lon=self.x)

    def get_googlemap_link(self) -> str:
        """
        Returns the URL for GSI Map with parameters.
        ex. https://maps.google.com/maps?q=24.197611,120.780512&z=18
        """
        if self.level is None or self.x is None or self.y is None:
            return ''

        url = 'https://maps.google.com/maps?q={lat:.6f},{lon:.6f}&z={level:d}'
        return url.format(
            level=9 + self.level,
            lat=self.y, lon=self.x)

    def is_inside(self, area: str) -> int:
        """
        Check if the node is inside the area specified by
        parent's names or jiscodes.

        Parameters
        ----------
        area: str
            Specify the area by name or jiscode.

        Returns
        -------
        int
            It returns 1 if the node is inside the region,
            0 if it is not inside, and -1 if it cannot be
            determined by this node.

        Notes
        -----
        If a city code is specified and the node is at
        the prefecture level, it will return 0 if the first two digits
        of the code do not match, otherwise it will return -1.
        """
        if re.match(r'\d{2}', area):
            # 2 digits prefecture code
            if self.get_pref_jiscode() == area:
                return 1

        if re.match(r'\d{5}', area):
            # 5 digits city code
            citycode = self.get_city_jiscode()
            if citycode == area:
                return 1

            if citycode != '':
                return 0

            if self.get_pref_jiscode() != area[0:2]:
                return 0
            else:
                return -1

        # Check if the standardized notation is included
        # in the parent nodes.
        parents = self.get_parent_list()
        area_index = default_itaiji_converter.standardize(area)
        if area_index in [n.name_index for n in parents]:
            return 1

        return 0
