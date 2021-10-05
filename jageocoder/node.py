from logging import getLogger
import re
from typing import List, NoReturn, Optional

from sqlalchemy import Column, ForeignKey, Integer, Float, String, Text
from sqlalchemy import or_
from sqlalchemy.orm import backref, relationship

from jageocoder.address import AddressLevel
from jageocoder.base import Base
from jageocoder.itaiji import converter as itaiji_converter

logger = getLogger(__name__)


class AddressNodeError(RuntimeError):
    pass


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
    name = Column(String(256), nullable=False)
    name_index = Column(String(256), nullable=False)
    x = Column(Float, nullable=True)
    y = Column(Float, nullable=True)
    level = Column(Integer, nullable=True)
    note = Column(Text, nullable=True)
    parent_id = Column(Integer, ForeignKey('node.id'), nullable=True)
    children = relationship(
        "AddressNode",
        cascade="all",
        backref=backref("parent", remote_side="AddressNode.id"),
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
        for c in self.children:
            if c.name == target_name or c.name_index == target_name:
                return c

        return None

    def search_recursive(self, index, session):
        """
        Search nodes recursively that match the specified address notation.

        Parameter
        ---------
        index : str
            The standardized address notation.
        session : sqlalchemy.orm.Session
            The database session for executing SQL queries.

        Return
        ------
        A list of relevant AddressNode.
        """
        l_optional_prefix = itaiji_converter.check_optional_prefixes(index)
        optional_prefix = index[0: l_optional_prefix]
        index = index[l_optional_prefix:]

        logger.debug("node:{}, index:{}, optional_prefix:{}".format(
            self, index, optional_prefix))
        if len(index) == 0:
            return [[self, optional_prefix]]

        conds = []

        if '0' <= index[0] and index[0] <= '9':
            # If it starts with a number,
            # look for a node that matches the numeric part exactly.
            for i in range(0, len(index)):
                if index[i] == '.':
                    break

            substr = index[0:i+1] + '%'
            conds.append(self.__class__.name_index.like(substr))
            logger.debug("  conds: name_index LIKE '{}'".format(substr))
        else:
            # If it starts with not a number,
            # look for a node with a maching first letter.
            substr = index[0:1] + '%'
            conds.append(self.__class__.name_index.like(substr))
            logger.debug("  conds: name_index LIKE '{}'".format(substr))

        filtered_children = session.query(self.__class__).filter(
            self.__class__.parent_id == self.id, or_(*conds))

        candidates = []
        for child in filtered_children:
            logger.debug("-> comparing; {}".format(child.name_index))

            if index.startswith(child.name_index):
                # In case the index string of the child node is
                # completely included in the beginning of the search string.
                # ex. index='東京都新宿区...' and child.name_index='東京都'
                offset = len(child.name_index)
                rest_index = index[offset:]
                logger.debug("child:{} match {} chars".format(child, offset))
                for cand in child.search_recursive(rest_index, session):
                    candidates.append([
                        cand[0],
                        optional_prefix + child.name_index + cand[1]
                    ])

                continue

            l_optional_postfix = itaiji_converter.check_optional_postfixes(
                child.name_index)
            if l_optional_postfix > 0:
                # In case the index string of the child node with optional
                # postfixes removed is completely included in the beginning
                # of the search string.
                # ex. index='2.-8.', child.name_index='2.番' ('番' is a postfix)
                child.name_index[-l_optional_postfix:]
                alt_child_index = child.name_index[0: -l_optional_postfix]
                if index.startswith(alt_child_index):
                    offset = len(alt_child_index)
                    if len(index) > offset and index[offset] == '-':
                        offset += 1

                    rest_index = index[offset:]
                    logger.debug(
                        "child:{} match {} chars".format(child, offset))
                    for cand in child.search_recursive(rest_index, session):
                        candidates.append([
                            cand[0],
                            optional_prefix + index[0: offset] + cand[1]
                        ])

                    continue

            if '条' in child.name_index:
                # Support for Sapporo City and other cities that use
                # "北3西1" instead of "北3条西１丁目".
                alt_name_index = child.name_index.replace('条', '', 1)
                if index.startswith(alt_name_index):
                    offset = len(alt_name_index)
                    rest_index = index[offset:]
                    logger.debug(
                        "child:{} match {} chars".format(child, offset))
                    for cand in child.search_recursive(rest_index, session):
                        candidates.append([
                            cand[0],
                            optional_prefix + alt_name_index + cand[1]
                        ])

                    continue

        if self.level == AddressLevel.WORD and self.parent.name == '京都市':
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
                    for cand in child.search_recursive(rest_index, session):
                        candidates.append([
                            cand[0],
                            optional_prefix + index[0: offset] + cand[1]
                        ])

        if len(candidates) == 0:
            candidates = [[self, optional_prefix]]

        logger.debug("node:{} returns {}".format(self, candidates))

        return candidates

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
        ['None', '[11460206:東京都(139.69164,35.6895)1(jisx0401:13)]', 'None', '[12063501:多摩市(139.446366,35.636959)3(jisx0402:13224)]', 'None', '[12065382:落合(139.427097,35.624877)5(None)]', '[12065383:一丁目(139.427097,35.624877)6(None)]', '[12065389:15番地(139.428969,35.625779)7(None)]']
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
        if node is None:
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
            AddressLevel.CITY, AddressLevel.WORD])
        if node is None:
            return ''

        return node.name

    def get_city_jiscode(self) -> str:
        """
        Returns the jisx0402 code of the city that
        contains this node.
        """
        node = self.retrieve_upper_node([
            AddressLevel.CITY, AddressLevel.WORD])
        if node is None:
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
