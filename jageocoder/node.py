from functools import lru_cache
import json
import logging
import re
from typing import List, Optional

from sqlalchemy import Column, Float, ForeignKey, Integer, SmallInteger, String, Text
from sqlalchemy import or_
from sqlalchemy.orm import deferred
from sqlalchemy.orm import backref, relationship

from jageocoder.address import AddressLevel
from jageocoder.aza_master import AzaMaster
from jageocoder.base import Base, get_session
from jageocoder.dataset import Dataset  #
from jageocoder.itaiji import Converter
from jageocoder.result import Result
from jageocoder.strlib import strlib


logger = logging.getLogger(__name__)
default_itaiji_converter = Converter()  # With default settings


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
    priority : int
        Priority assigned to each source of data.
        Smaller value indicates higher priority.
    note : string
        Note or comment.
    parent_id : int
        The id of the parent node.
    children : list of AddressNode
        The child nodes.
    dataset : source dataset where the node come from.
    """
    __tablename__ = 'node'

    id = Column(Integer, primary_key=True)
    name = deferred(Column(String(256), nullable=False))
    name_index = Column(String(256), nullable=False)
    x = deferred(Column(Float, nullable=True))
    y = deferred(Column(Float, nullable=True))
    level = Column(SmallInteger, nullable=True)
    priority = Column(SmallInteger, ForeignKey('dataset.id'), nullable=True)
    note = deferred(Column(Text, nullable=True))
    parent_id = Column(Integer, ForeignKey('node.id'), nullable=True)
    children = relationship(
        "AddressNode",
        cascade="all",
        backref=backref("parent", remote_side="AddressNode.id"),
        lazy="dynamic",
    )
    dataset = relationship(Dataset, cascade="all")

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
        self.name_index = default_itaiji_converter.standardize(self.name)

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
        self.priority = kwargs.get('priority', 99)
        self.note = kwargs.get('note', None)

    def add_child(self, child):
        """
        Add a node as a child of this node.

        Parameters
        ----------
        child : AddressNode
            The node that will be a child node.
        """
        self.children.append(child)

    def add_to_parent(self, parent):
        """
        Add this node as a child of an other node.

        Parameters
        ----------
        parent : AddressNode
            The node that will be the parent.
        """
        self.parent = parent

    def get_child(self, target_name: str):
        """
        Get a child node with the specified name.

        Parameters
        ----------
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
    def search_child_with_criteria(
            self,
            pattern: str,
            max_level: Optional[int] = None,
            require_coordinates: bool = False):
        conds = []
        conds.append(AddressNode.name_index.like(pattern))
        logger.debug("  conds: name_index LIKE '{}'".format(pattern))

        if max_level is not None:
            conds.append(AddressNode.level <= max_level)
            logger.debug("    and level <= {}".format(max_level))

        if require_coordinates is True:
            conds.append(AddressNode.y < 90.0)
            logger.debug("    and having valid coordinates")

        filtered_children = self.children.filter(*conds).order_by(
            AddressNode.id)
        logger.debug("  -> {} found.".format(filtered_children.count()))
        return filtered_children

    def search_recursive(
        self, index: str, tree: 'AddressTree',  # noqa
        processed_nodes: Optional[List['AddressNode']] = None
    ) -> List[Result]:
        """
        Search nodes recursively that match the specified address notation.

        Parameters
        ----------
        index : str
            The standardized address notation.
        processed_nodes: List of AddressNode, optional
            List of nodes that have already been processed
            by TRIE search results

        Return
        ------
        A list of relevant AddressNode.
        """
        l_optional_prefix = tree.converter.check_optional_prefixes(index)
        optional_prefix = index[0: l_optional_prefix]
        index = index[l_optional_prefix:]

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
            pattern=substr,
            max_level=max_level,
            require_coordinates=tree.get_config('require_coordinates'))

        # Check if the index begins with an extra character of
        # the current node.
        if filtered_children.count() == 0 and \
                index[0] in tree.converter.extra_characters:
            logger.debug("Beginning with an extra character: {}".format(
                index[0]))
            candidates = self.search_recursive(
                index=index[1:], tree=tree,
                processed_nodes=processed_nodes)
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
            if filtered_children.count() == 0:
                msg = 'No candidates. Children are; {}'.format(
                    ','.join([x.name for x in self.children]))
            else:
                msg = 'Filtered children are; {}'.format(
                    ','.join([x.name for x in filtered_children]))

            logger.debug(msg)

        candidates = []
        for child in filtered_children:
            if child in processed_nodes or []:
                msg = "-> Skip {}({}) (already processed)."
                logger.debug(msg.format(child.name, child.id))
                continue

            logger.debug("-> comparing; {}".format(child.name_index))
            new_candidates = self._get_candidates_from_child(
                child=child,
                index=index,
                optional_prefix=optional_prefix,
                tree=tree,
                processed_nodes=processed_nodes)

            if len(new_candidates) > 0:
                candidates += new_candidates

        if self.level == AddressLevel.WARD and self.parent.name == '京都市':
            # Street name (通り名) support in Kyoto City
            # If a matching part of the search string is found in the
            # child nodes, the part before the name is skipped
            # as a street name.
            for child in self.children:
                pos = index.rfind(child.name_index)
                if pos <= 0:
                    continue

                offset = pos + len(child.name_index)
                rest_index = index[offset:]
                logger.debug(
                    "child:{} match {} chars".format(child, offset))
                for cand in child.search_recursive(
                        index=rest_index,
                        tree=tree,
                        processed_nodes=processed_nodes):
                    candidates.append(Result(
                        cand[0],
                        optional_prefix +
                        index[0: offset] + cand[1],
                        l_optional_prefix +
                        len(child.name_index) + len(cand[1])))

        # Search for subnodes with queries excludes Aza-name candidates
        aza_skip = tree.get_config('aza_skip')
        omissible_index = ""   # Skip = off
        if aza_skip is True:   # Skip = on
            omissible_index = index
        elif aza_skip is None:  # Skip = auto
            omissible_index = self.get_omissible_index(
                index, tree, processed_nodes)

        if omissible_index != "":
            msg = "Checking Aza-name, current_node:{}, processed:{}"
            logger.debug(msg.format(self, processed_nodes))
            aza_positions = tree.converter.optional_aza_len(
                index, 0)
            aza_positions.append(len(omissible_index))
            if len(index) in aza_positions:
                aza_positions.remove(len(index))

            aza_positions.sort()

            for azalen in aza_positions:
                if azalen > len(omissible_index):
                    break

                msg = '"{}" in index "{}" can be optional.'
                logger.debug(msg.format(index[:azalen], index))
                # Note: Disable 'aza_skip' here not to perform
                # repeated skip processing.
                tree.set_config(aza_skip=False)
                sub_candidates = self.search_recursive(
                    index=index[azalen:],
                    tree=tree,
                    processed_nodes=processed_nodes)
                tree.set_config(aza_skip=aza_skip)
                if sub_candidates[0].matched == '':
                    continue

                for cand in sub_candidates:
                    if cand.node.level < AddressLevel.BLOCK and \
                            cand.node.name_index not in \
                            tree.converter.chiban_heads:
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
            tree: 'AddressTree',  # noqa
            processed_nodes: List['AddressNode']) -> list:
        """
        Get candidates from the child.

        Parameters
        ----------
        child: AddressNode
            The starting child node.
        index: str
            Standardized query string. Numeric characters are kept as
            original notation.
        tree: AddressTree
            The address tree.
        optional_prefix: str
            The option string that preceded the string passed by index.

        Returns
        -------
        list
            The list of candidates.
            Each element of the array has the matched AddressNode
            as the first element and the matched string
            as the second element.
        """

        match_len = tree.converter.match_len(index, child.name_index)
        if match_len == 0:
            l_optional_postfix = tree.converter.check_optional_postfixes(
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
                match_len = tree.converter.match_len(
                    index, alt_child_index, removed_postfix=optional_postfix)
                if match_len < len(index) and index[match_len] in '-ノ':
                    match_len += 1

        if match_len == 0 and child.name_index.endswith('.条'):
            # Support for Sapporo City and other cities that use
            # "北3西1" instead of "北3条西１丁目".
            alt_child_index = child.name_index.replace('条', '', 1)
            logger.debug("child:{} ends with '.条'".format(child))
            match_len = tree.converter.match_len(index, alt_child_index)

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
                tree=tree,
                processed_nodes=processed_nodes):
            candidates.append(Result(
                cand.node,
                optional_prefix + index[0:match_len] + cand.matched,
                l_optional_prefix + match_len + cand.nchars))

        return candidates

    def get_omissible_index(
            self,
            index: str,
            tree: 'AddressTree',  # noqa
            processed_nodes: List['AddressNode']) -> str:
        """
        Obtains an optional leading substring from the search string index.

        Parameters
        ----------
        index: str
            Target string.
        tree: AddressTree
            Current working tree object.
        processed_nodes: List of AddressNode
            List of nodes that have already been processed
            by TRIE search results.

        Returns
        -------
        str
            The optional leading substring.
            If not omissible, an empty string is returned.

        Notes
        -----
        Retrieve the lower address elements of this node
        that have start_count_type is 1 from the aza_master.

        If the name of the element is contained in the index,
        the substring before the name is returned.
        """
        if self.level < AddressLevel.CITY or \
                self.level > AddressLevel.AZA:
            return ""

        for node in processed_nodes or []:
            if node.parent_id == self.parent_id:
                logger.debug((
                    "Can't skip substring after '{}', "
                    "a sibling node {} had been selected").format(
                        self.name, node.name))
                return ""

            elif node.parent_id == self.id:
                logger.debug((
                    "Can't skip substring after '{}', "
                    "a child node {} had been selected").format(
                        self.name, node.name))
                return ""

        if self.level < AddressLevel.OAZA:
            target_prefix = self.get_city_jiscode()
        else:
            target_prefix = self.get_aza_code().rstrip('0')

        if target_prefix == "":
            logger.debug((
                "Can't skip substring after '{}', "
                "the node {} doesn't have city/aza code.").format(
                    self.name, self.name))
            return ""

        # self_names = self.get_fullname()
        omissible_index = index
        for aza_row in tree.session.query(AzaMaster).filter(
                AzaMaster.code.like('{}%'.format(target_prefix)),
                AzaMaster.aza_class == 3,
                AzaMaster.start_count_type == 1):

            # logger.debug("Checking {}.".format(aza_row.names))

            logger.debug("  -> {} is not omissible.".format(
                aza_row.names))

            names = json.loads(aza_row.names)
            name = tree.converter.standardize(names[-1][1])
            pos = omissible_index.find(name)
            if pos >= 0:
                logger.debug(
                    "Can't ommit substring '{}' in {}".format(
                        names[-1][1], omissible_index))
                omissible_index = omissible_index[0:pos]
                if pos == 0:
                    break

        return omissible_index

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
            "priority": self.priority,
            "note": self.note,
            "fullname": self.get_fullname(),
        }

    def as_geojson(self):
        """
        Return the geojson notation of the node.
        """
        return {
            "type": "Feature",
            "geometry": {
                "type": "Point",
                "coordinates": [self.x, self.y]
            },
            "properties": {
                "id": self.id,
                "name": self.name,
                "level": self.level,
                "priority": self.priority,
                "note": self.note,
                "fullname": self.get_fullname(),
            }
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

            node = node.parent
            if node is None:
                break

        return ''

    def get_aza_code(self) -> str:
        """
        Returns the 'AZA-code' concatinated with the city-code
        and the aza-id containing this node.
        """
        aza_id = self.get_aza_id()
        if aza_id != '':
            return self.get_city_jiscode() + aza_id

        return ''

    def get_aza_names(self) -> list:
        """
        Returns representation of Aza node containing this node.

        Returns
        -------
        list
            A list containing notations from the prefecture level
            to the Aza level in the following format:

            [AddressLevel, Kanji, Kana, English, code]
        """
        if self.level >= AddressLevel.OAZA:
            code = self.get_aza_code()
        elif self.level >= AddressLevel.CITY:
            code = self.get_city_jiscode()
        else:
            code = self.get_pref_jiscode()

        aza_record = AzaMaster.search_by_code(
            code, get_session(self))
        if aza_record:
            return json.loads(aza_record.names)

        return []

    def get_postcode(self) -> str:
        """
        Returns the 7digit postcode of the oaza that
        contains this node.
        """
        node = self
        while True:
            if node.level <= AddressLevel.COUNTY:
                break

            if node.note and 'postcode' in node.note:
                m = re.search(r'postcode:(\d{7})', node.note)
                if m:
                    return m.group(1)

            node = node.parent

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
