from functools import lru_cache
import logging
import re
from typing import List, Optional, Union

from sqlalchemy import Column, ForeignKey, Integer, Float, String, Text
from sqlalchemy import or_
from sqlalchemy.orm import deferred
from sqlalchemy.orm import backref, relationship

from jageocoder.address import AddressLevel
from jageocoder.base import Base
from jageocoder.itaiji import converter as itaiji_converter
from jageocoder.result import Result
from jageocoder.strlib import strlib

logger = logging.getLogger(__name__)


class AddressNode(Base):
    """
    The address-node structure stored in 'node' table.

    Attributes
    ----------
    id : int
        The key identifier that is automatically sequentially numbered.
    name : str
        The name of the address element, such as '東京都' or '新宿区'
    name_index : str
        The standardized string for indexing created from its name.
    x : float
        X-coordinate value. (Longitude)
    y : float
        Y-coordinate value. (Latitude)
    level : int
        The level of the address element.
        The meaning of each value is as follows.
    note : string
        Note or comment.
    parent_id : int
        The id of the parent node.
    children : list of AddressNode
        The child nodes.
    """
    __tablename__ = 'node'

    id = Column(Integer, primary_key=True)
    name = deferred(Column(String(256), nullable=False))
    name_index = Column(String(256), nullable=False)
    x = deferred(Column(Float, nullable=True))
    y = deferred(Column(Float, nullable=True))
    level = Column(Integer, nullable=True)
    note = deferred(Column(Text, nullable=True))
    parent_id = Column(Integer, ForeignKey('node.id'), nullable=True)
    children = relationship(
        "AddressNode",
        cascade="all",
        backref=backref("parent", remote_side="AddressNode.id"),
        lazy="dynamic",
    )

    def __init__(self, *args, **kwargs):
        """
        The initializer of the node.

        In addition to the initialization of the record,
        the name_index is also created.
        """
        super().__init__(*args, **kwargs)
        # Basic attributes
        self.name = kwargs.get('name', '')

        # Set extended attributes
        self.set_attributes(**kwargs)

        # For indexing
        self.name_index = itaiji_converter.standardize(self.name)

        # Relations
        self.parent_id = kwargs.get('parent_id', None)

    def set_attributes(self, **kwargs):
        """
        Set attributes of this node by kwargs values.
        'name' can't be modified.
        """
        self.x = kwargs.get('x', kwargs.get('lon'))
        self.y = kwargs.get('y', kwargs.get('lat'))
        self.level = kwargs.get('level')
        self.note = kwargs.get('note', None)

    def add_child(self, child):
        """
        Add a node as a child of this node.

        Parameter
        ---------
        child : AddressNode
            The node that will be a child node.
        """
        self.children.append(child)

    def add_to_parent(self, parent):
        """
        Add this node as a child of an other node.

        Parameter
        ---------
        parent : AddressNode
            The node that will be the parent.
        """
        self.parent = parent

    def get_child(self, target_name):
        """
        Get a child node with the specified name.

        Parameter
        ---------
        target_name : str
            The name (or standardized name) of the target node.

        Return
        ------
        Returns the relevand node if it is found,
        or None if it is not.
        """
        return self.children.filter(or_(
            AddressNode.name == target_name,
            AddressNode.name_index == target_name
        )).one_or_none()

    @lru_cache(maxsize=512)
    def search_child_with_criteria(self, pattern: str,
                                   max_level: Optional[int] = None):
        conds = []
        conds.append(AddressNode.name_index.like(pattern))
        logger.debug("  conds: name_index LIKE '{}'".format(pattern))

        if max_level is not None:
            conds.append(AddressNode.level <= max_level)
            logger.debug("    and level <= {}".format(max_level))

        filtered_children = self.children.filter(*conds).order_by(
            AddressNode.id)
        return filtered_children

    def search_recursive(
            self, index: str,
            processed_nodes: Optional[List['AddressNode']] = None,
            aza_skip: Union[str, bool, None] = None) -> List[Result]:
        """
        Search nodes recursively that match the specified address notation.

        Parameter
        ---------
        index : str
            The standardized address notation.
        processed_nodes: List of AddressNode, optional
            List of nodes that have already been processed
            by TRIE search results
        aza_skip: str, bool, optional
            Specifies how to skip aza-names.
            - Set to 'auto' or None to make the decision automatically
            - Set to 'off' or False to not skip
            - Set to 'on'　or True to always skip

        Return
        ------
        A list of relevant AddressNode.
        """
        l_optional_prefix = itaiji_converter.check_optional_prefixes(index)
        optional_prefix = index[0: l_optional_prefix]
        index = index[l_optional_prefix:]

        if aza_skip in (None, ''):
            aza_skip = 'auto'
        elif aza_skip in (True, 'enable'):
            aza_skip = 'on'
        elif aza_skip in (False, 'disable'):
            aza_skip = 'off'

        logger.debug("node:{}, index:{}, optional_prefix:{}".format(
            self, index, optional_prefix))
        if len(index) == 0:
            return [Result(self, optional_prefix, 0)]

        max_level = None
        v = strlib.get_number(index)
        if v['i'] > 0:
            # If it starts with a number,
            # look for a node that matches the numeric part exactly.
            substr = '{}.%'.format(v['n'])
        else:
            # If it starts with not a number,
            # look for a node with a maching first letter.
            substr = index[0:1] + '%'

        if '字' in optional_prefix:
            max_level = AddressLevel.AZA

        filtered_children = self.search_child_with_criteria(
            pattern=substr, max_level=max_level)

        # Check if the index begins with an extra character of
        # the current node.
        if filtered_children.count() == 0 and \
                index[0] in itaiji_converter.extra_characters:
            logger.debug("Beginning with an extra character: {}".format(
                index[0]))
            candidates = self.search_recursive(
                index[1:], processed_nodes, aza_skip)
            if len(candidates) > 0:
                new_candidates = []
                for candidate in candidates:
                    new_candidate = Result(
                        candidate.node,
                        index[0] + candidate.matched,
                        l_optional_prefix + candidate.nchars)
                    new_candidates.append(new_candidate)

                return new_candidates

            return []

        if logger.isEnabledFor(logging.DEBUG):
            msg = 'No candidates. Children are; {}'.format(
                ','.join([x.name for x in self.children]))
            logger.debug(msg)

        candidates = []
        for child in filtered_children:
            if child in processed_nodes or []:
                logger.debug("-> skipped; {}({})".format(
                    child.name, child.id))
                continue

            logger.debug("-> comparing; {}".format(child.name_index))
            new_candidates = self._get_candidates_from_child(
                child=child,
                index=index,
                optional_prefix=optional_prefix,
                processed_nodes=processed_nodes,
                aza_skip=aza_skip)

            if len(new_candidates) > 0:
                candidates += new_candidates

        if self.level == AddressLevel.WARD and self.parent.name == '京都市':
            # Street name (通り名) support in Kyoto City
            # If a matching part of the search string is found in the
            # child nodes, the part before the name is skipped
            # as a street name.
            for child in self.children:
                pos = index.find(child.name_index)
                if pos > 0:
                    offset = pos + len(child.name_index)
                    rest_index = index[offset:]
                    logger.debug(
                        "child:{} match {} chars".format(child, offset))
                    for cand in child.search_recursive(
                            rest_index,
                            processed_nodes, aza_skip):
                        candidates.append(
                            Result(cand[0],
                                   optional_prefix +
                                   index[0: offset] + cand[1],
                                   l_optional_prefix +
                                   len(child.name_index) + len(cand[1])
                                   ))

        # Search for subnodes with queries excludes Aza-name candidates
        if aza_skip == 'on' or \
                (aza_skip == 'auto' and
                 self._is_aza_omission_target(processed_nodes)):
            msg = "Checking Aza-name, current_node:{}, processed:{}"
            logger.debug(msg.format(self, processed_nodes))
            aza_positions = itaiji_converter.optional_aza_len(
                index, 0)

            if len(aza_positions) > 0:
                for azalen in aza_positions:
                    msg = '"{}" in index "{}" can be optional.'
                    logger.debug(msg.format(index[:azalen], index))
                    # Note: Disable 'aza_skip' here not to perform
                    # repeated skip processing.
                    sub_candidates = self.search_recursive(
                        index[azalen:],
                        processed_nodes, aza_skip='off')
                    if sub_candidates[0].matched == '':
                        continue

                    for cand in sub_candidates:
                        if cand.node.level < AddressLevel.BLOCK and \
                                cand.node.name_index not in \
                                itaiji_converter.chiban_heads:
                            logger.debug("{} is ignored".format(
                                cand.node.name))
                            continue

                        candidates.append(Result(
                            cand.node,
                            optional_prefix +
                            index[0:azalen] + cand.matched,
                            l_optional_prefix + cand.nchars))

        if len(candidates) == 0:
            candidates = [Result(self, '', 0)]

        logger.debug("node:{} returns {}".format(self.name, candidates))
        return candidates

    def _get_candidates_from_child(
            self, child: 'AddressNode',
            index: str, optional_prefix: str,
            processed_nodes: List['AddressNode'],
            aza_skip: str) -> list:
        """
        Get candidates from the child.

        Parameters
        ----------
        child: AddressNode
            The starting child node.
        index: str
            Standardized query string. Numeric characters are kept as
            original notation.
        optional_prefix: str
            The option string that preceded the string passed by index.
        aza_skip: str
            Specifies how to skip aza-names.
            Options are 'auto', 'off', and 'on'

        Returns
        -------
        list
            The list of candidates.
            Each element of the array has the matched AddressNode
            as the first element and the matched string
            as the second element.
        """

        match_len = itaiji_converter.match_len(index, child.name_index)
        if match_len == 0:
            l_optional_postfix = itaiji_converter.check_optional_postfixes(
                child.name_index, child.level)
            if l_optional_postfix > 0:
                # In case the index string of the child node with optional
                # postfixes removed is completely included in the beginning
                # of the search string.
                # ex. index='2.-8.', child.name_index='2.番' ('番' is a postfix)
                optional_postfix = child.name_index[-l_optional_postfix:]
                alt_child_index = child.name_index[0: -l_optional_postfix]
                logger.debug(
                    "child:{} has optional postfix {}".format(
                        child, optional_postfix))
                match_len = itaiji_converter.match_len(
                    index, alt_child_index, removed_postfix=optional_postfix)
                if match_len < len(index) and index[match_len] in '-ノ':
                    match_len += 1

        if match_len == 0 and child.name_index.endswith('.条'):
            # Support for Sapporo City and other cities that use
            # "北3西1" instead of "北3条西１丁目".
            alt_child_index = child.name_index.replace('条', '', 1)
            logger.debug("child:{} ends with '.条'".format(child))
            match_len = itaiji_converter.match_len(index, alt_child_index)

        if match_len == 0:
            logger.debug("{} doesn't match".format(child.name))
            return []

        candidates = []
        offset = match_len
        rest_index = index[offset:]
        l_optional_prefix = len(optional_prefix)
        logger.debug("child:{} match {} chars".format(child, offset))
        for cand in child.search_recursive(
                index=rest_index,
                processed_nodes=processed_nodes,
                aza_skip=aza_skip):
            candidates.append(Result(
                cand.node,
                optional_prefix + index[0:match_len] + cand.matched,
                l_optional_prefix + match_len + cand.nchars))

        return candidates

    def _is_aza_omission_target(
            self, processed_nodes: List['AddressNode']) -> bool:
        """
        Determine if this node is a target of aza-name omission.

        Parameters
        ----------
        processed_nodes: List of AddressNode
            List of nodes that have already been processed
            by TRIE search results

        Returns
        -------
        bool
            True if this node is a target of aza-name ommission.
            Otherwise False.

        Notes
        -----
        Sibling and parent nodes of nodes whose names match in TRIE
        should not look for nodes that omit the aza-names.
        """
        if self.level < AddressLevel.CITY or \
                self.level > AddressLevel.AZA:
            return False

        for node in processed_nodes or []:
            if node.parent_id == self.parent_id:
                logger.debug("A sibling node {} had been selected".format(
                    node.name))
                return False

            elif node.parent_id == self.id:
                logger.debug("A child node {} had been selected".format(
                    node.name))
                return False

        if self.level in (AddressLevel.CITY, AddressLevel.WARD):
            return True

        aza_children = self.children.filter(
            AddressNode.level <= AddressLevel.AZA)
        for child in aza_children:
            if child.name_index not in itaiji_converter.chiban_heads:
                logger.debug(("The child-node {} is higher than Aza "
                              "(can't skip aza-names)").format(child.name))
                return False

        return True

    def save_recursive(self, session):
        """
        Add the node to the database recursively.

        Parameters
        ----------
        session : sqlalchemy.orm.Session
            The database session for executing SQL queries.
        """
        session.add(self)
        for c in self.children:
            c.save_recursive(session)

    def as_dict(self):
        """
        Return the dict notation of the node.
        """
        return {
            "id": self.id,
            "name": self.name,
            "x": self.x,
            "y": self.y,
            "level": self.level,
            "note": self.note,
            "fullname": self.get_fullname(),
        }

    def get_fullname(self):
        """
        Returns a complete address notation starting with the name of
        the prefecture.
        """
        names = []
        cur_node = self
        while cur_node.parent:
            names.insert(0, cur_node.name)
            cur_node = cur_node.parent

        return names

    def get_parent_list(self):
        """
        Returns a complete node list starting with the prefecture.
        """
        nodes = []
        cur_node = self
        while cur_node.parent:
            nodes.insert(0, cur_node)
            cur_node = cur_node.parent

        return nodes

    def get_nodes_by_level(self):
        """
        The function returns an array of this node and its upper nodes.
        The Nth node of the array contains the node corresponding
        to address level N.
        If there is no element corresponding to level N, None is stored.

        Example
        -------
        >>> import jageocoder
        >>> jageocoder.init()
        >>> node = jageocoder.searchNode('多摩市落合1-15')[0][0]
        >>> [str(x) for x in node.get_node_array_by_level()]
        ['None', '[11460206:東京都(139.69164,35.6895)1(jisx0401:13)]', 'None', '[12063501:多摩市(139.446366,35.636959)3(jisx0402:13224)]', 'None',
                                '[12065382:落合(139.427097,35.624877)5(None)]', '[12065383:一丁目(139.427097,35.624877)6(None)]', '[12065389:15番地(139.428969,35.625779)7(None)]']
        """
        result = [None] * (self.level + 1)
        cur_node = self
        while cur_node.parent:
            result[cur_node.level] = cur_node
            cur_node = cur_node.parent

        return result

    def __str__(self):
        return '[{}:{}({},{}){}({})]'.format(
            self.id, self.name, self.x, self.y, self.level, str(self.note))

    def __repr__(self):
        r = []
        cur_node = self
        while cur_node.parent:
            r.insert(0, str(cur_node))
            cur_node = cur_node.parent

        return '>'.join(r)

    def retrieve_upper_node(self, target_levels: List[int]):
        """
        Retrieves the node at the specified level from
        the this node or one of its upper nodes.
        """
        cur_node = self
        while cur_node.parent and cur_node.level not in target_levels:
            parent = cur_node.parent
            cur_node = parent

        if cur_node.level in target_levels:
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

    def get_postcode(self) -> str:
        """
        Returns the 7digit postcode of the oaza that
        contains this node.
        """
        node = self
        while True:
            if node.level <= AddressLevel.COUNTY:
                return ''

            if node.note:
                break

            node = node.parent

        m = re.search(r'postcode:(\d{7})', node.note)
        if m:
            return m.group(1)

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