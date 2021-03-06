from collections import OrderedDict
import copy
import json
from logging import getLogger
import os

import marisa_trie
from sqlalchemy import Column, ForeignKey, Integer, Float, String, Text
from sqlalchemy import Index
from sqlalchemy import or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from jageocoder.itaiji import converter as itaiji_converter

Base = declarative_base()
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


class AddressLevelError(RuntimeError):
    pass


class AddressLevel(object):
    """
    Address Levels

    1 = 都道府県
    2 = 郡・支庁・振興局
    3 = 市町村および特別区
    4 = 政令市の区
    5 = 大字
    6 = 字
    7 = 地番または住居表示実施地域の街区
    8 = 枝番または住居表示実施地域の住居番号
    """

    # Constants
    UNDEFINED = -1
    PREF = 1
    COUNTY = 2
    CITY = 3
    WORD = 4
    OAZA = 5
    AZA = 6
    BLOCK = 7
    BLD = 8

    @classmethod
    def guess(cls, name, parent, trigger):
        """
        Guess the level of the address element.

        Parameters
        ----------
        name : str
            The name of the address element
        parent : AddressNode
            The parent node of the target.
        trigger : dict
            properties of the new address node who triggered
            adding the address element.

            name : str. name. ("２丁目")
            x : float. X coordinate or longitude. (139.69175)
            y : float. Y coordinate or latitude. (35.689472)
            level : int. Address level (1: pref, 3: city, 5: oaza, ...)
            note : str. Note.
        """
        lastchar = name[-1]
        if parent.id == -1:
            return cls.PREF

        if parent.level == cls.PREF and \
                (lastchar == '郡' or name.endswith(('支庁', '振興局',))):
            return cls.COUNTY

        if lastchar in '市町村':
            if parent.level < cls.CITY:
                return cls.CITY

            if parent.level in (cls.CITY, cls.OAZA,):
                return parent.level + 1

        if lastchar == '区':
            if parent.level == cls.CITY:
                return cls.WORD

            if parent.name == '東京都':
                return cls.CITY

        if parent.level < cls.OAZA:
            return cls.OAZA

        if parent.level == cls.OAZA:
            return cls.AZA

        if parent.level == cls.AZA:
            if trigger['level'] <= cls.BLOCK:
                # If the Aza-name is over-segmented, Aza-level address elements
                # may appear in series.
                # ex: 北海道,帯広市,稲田町南,九線,西,19番地
                return cls.AZA

            return cls.BLOCK

        raise AddressLevelError(
            ('Cannot estimate the level of the address element. '
                'name={}, parent={}, trigger={}'.format(
                    name, parent, trigger)))


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

        In addition to the initialization of the record, the name_index is also created.
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
        Recursively searches for nodes that match the specified address notation.

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
                optional_postfix = child.name_index[-l_optional_postfix:]
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
        Returns a complete address notation starting with the name of the prefecture.
        """
        names = []
        cur_node = self
        while cur_node.parent:
            names.insert(0, cur_node.name)
            cur_node = cur_node.parent

        return names

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


class TrieNode(Base):
    """
    The mapping-table of TRIE id and Node id. Stored in 'trienode' table.

    Attributes
    ----------
    id : int
        The key identifier that is automatically sequentially numbered.
    trie_id : int
        TRIE id that corresponds one-to-one to a notation.
    node_id : int
        Node id that corresponds one-to-one to an AddressNode.
    node : AddressNode
        The node with node_id as its id.

    Note
    ----
    Some of the notations correspond to multiple address elements.
    For example, "中央区中央" exists in either 千葉市 and 相模原市,
    so TRIE id and Node id correspond one-to-many.
    """

    __tablename__ = 'trienode'

    id = Column(Integer, primary_key=True)
    trie_id = Column(Integer, nullable=False)
    node_id = Column(Integer, ForeignKey('node.id'), nullable=False)

    node = relationship("AddressNode")


class AddressTrie(object):
    """
    Implementation of TRIE Index using marisa trie.

    Attributes
    ----------
    path : str
        TRIE file path.
    trie : marisa_trie.Trie object
        TRIE index containing address notations higher than the oaza name.
    words : dict
        A dict whose key is the address notation to be registered.
        Note that the address notations must be standardized.
        The value can be anything, as it is used as a hash table
        to quickly determine if the notation is registered or not.
    """

    def __init__(self, path, words: dict = {}):
        """
        The initializer.

        Parameters
        ----------
        path : str
            Path to the TRIE file.
            Used both to open an existing file and to create a new file.
        words : dict (default : {})
            A dict whose key is the address notation to be registered.
        """
        self.path = path
        self.trie = None
        self.words = words

        if os.path.exists(path):
            self.connect()

    def connect(self):
        """
        Open the TRIE file.
        """
        self.trie = marisa_trie.Trie().mmap(self.path)

    def add(self, word: str):
        """
        Add an word to the words hash table.
        """
        self.words[word] = True

    def save(self):
        """
        Create a new TRIE index from the address notation registered in words,
        and save it to a file.
        """
        if self.trie:
            del self.trie

        if os.path.exists(self.path):
            os.remove(self.path)

        self.trie = marisa_trie.Trie(self.words.keys())
        self.trie.save(self.path)

        del self.trie
        self.connect()

    def get_id(self, query: str):
        """
        Get the id on the TRIE index (TRIE id) of the prefix string
        that exactly matches the string specified in query.
        Note that the prefix strings are standardized address notations.

        Parameters
        ----------
        query : str
            The query string.

        Return
        ------
        The TRIE id if it matches the query.
        Otherwise, it will raise a 'KeyError' exception.
        """
        return self.trie.key_id(query)

    def common_prefixes(self, query: str):
        """
        Returns a list of prefixes included in the query.
        Note that the prefix strings are standardized address notations.

        For example, '東京都新宿区' will return the following result.
        ```json
        {'東': 219, '東京': 26527, '東京都': 46587,
        '東京都新宿': 179816, '東京都新宿区': 217924}
        ```

        Parameters
        ----------
        query : str
            The query string.

        Return
        ------
        A dict with a prefix string as key and a TRIE id as value.
        """
        results = {}
        for p in self.trie.iter_prefixes(query):
            results[p] = self.trie.key_id(p)

        return results

    def predict_prefixes(self, query: str):
        """
        Returns a list of prefixes containing the query.
        Note that the prefix strings are standardized address notations.

        For example, '東京都新宿区西' will return the following result.
        ```json
        {'東京都新宿区西新宿': 341741, '東京都新宿区西早稲田': 341742,
        '東京都新宿区西5.軒町': 320459, '東京都新宿区西落合': 320460}
        ```

        Parameters
        ----------
        query : str
            The query string.

        Return
        ------
        A dict with a prefix string as key and a TRIE id as value.
        """
        results = {}
        for p in self.trie.iterkeys(query):
            results[p] = self.trie.key_id(p)

        return results


class AddressTree(object):
    """
    The address-tree structure.

    Attributes
    ----------
    dsn : str
        RFC-1738 based database-url, so called "data source name".
    trie_path : str
        File path to save the TRIE index.
    engine : sqlalchemy.engine.Engine
        The database engine which is used to connect to the database.
    conn : sqlalchemy.engine.Connection
        The connection object which is used to communicate witht the database.
    session : sqlalchemy.orm.Session
        The session object used for a series of database operations.
    root : AddressNode
        The root node of the tree.
    trie : AddressTrie
        The TRIE index of the tree.
    """

    def __init__(self, dsn=None, trie_path=None, **kwargs):
        """
        The initializer

        Parameters
        ----------
        dsn : str (Optional)
            Data Source Name of the database.
            Default:'sqlite:///db/address.db'
        trie_path : str (Optional)
            File path to save the TRIE index.
            Default:'./db/address.trie'
        debug : bool (Optional)
            Debugging flag, default:False
        """
        # Set default values
        self.dsn = dsn
        if self.dsn is None:
            self.dsn = 'sqlite:///db/address.db'

        self.trie_path = trie_path
        if self.trie_path is None:
            self.trie_path = './db/address.trie'

        # Options
        self.debug = kwargs.get('debug', False)

        # Database connection
        try:
            self.engine = create_engine(self.dsn, echo=self.debug)
            _session = sessionmaker()
            _session.configure(bind=self.engine)
            self.conn = self.engine.connect()
            self.session = _session()
        except Exception as e:
            logger.error(e)
            exit(1)

        self.root = None
        self.trie = AddressTrie(self.trie_path)

    def create_db(self):
        """
        Create database and tables.
        """
        Base.metadata.create_all(self.engine)

    def get_session(self):
        """
        Get the database session.

        Returns
        -------
        The sqlalchemy.orm.Session object.
        """
        return self.session

    def get_root(self):
        """
        Get the root-node of the tree.
        If not set yet, create and get the node from the database.

        Returns
        The AddressNode object.
        """
        if self.root:
            return self.root

        # Try to get root from the database
        session = self.get_session()
        try:
            self.root = session.query(
                AddressNode).filter_by(name='_root_').one()
        except NoResultFound:
            # Create a new root
            self.root = AddressNode(id=-1, name="_root_", parent_id=None)

        return self.root

    def add_address(self, address_names, do_update=False,
                    cache=None, **kwargs):
        """
        Create a new AddressNode and add to the tree.

        Parameters
        ----------
        address_names : list of str
            A list of the parent's address name.
            For example, ["東京都","新宿区","西新宿"]
        do_update : bool
            When an address with the same name already exists,
            update it with the value of kwargs if 'do_update' is true,
            otherwise do nothing.
        cache : LRU
            A dict object to use as a cache for improving performance,
            whose keys are the address notation from the prefecture level
            and whose values are the corresponding nodes.
            If not specified or None is given, do not use the cache.
        **kwargs : properties of the new address node.
            name : str. name. ("２丁目")
            x : float. X coordinate or longitude. (139.69175)
            y : float. Y coordinate or latitude. (35.689472)
            level : int. Address level (1: pref, 3: city, 5: oaza, ...)
            note : str. Note.

        Return
        ------
        The added node.
        """
        cur_node = self.get_root()
        for i, name in enumerate(address_names):
            fullname = ''.join(address_names[0:i + 1])
            if cache is not None:
                if fullname in cache:
                    cur_node = cache[fullname]
                    continue
                else:
                    logger.debug("Cache miss: '{}'".format(fullname))

            name_index = itaiji_converter.standardize(name)
            node = cur_node.get_child(name_index)
            if not node:
                if i < len(address_names) - 1:
                    guessed_level = AddressLevel.guess(
                        name, parent=cur_node, trigger=kwargs)
                else:
                    guessed_level = kwargs['level']

                kwargs.update({'name': name, 'parent': cur_node,
                               'level': guessed_level})
                new_node = AddressNode(**kwargs)
                cur_node.add_child(new_node)
                cur_node = new_node
            else:
                cur_node = node
                if i == len(address_names) - 1:
                    if do_update:
                        cur_node.set_attributes(**kwargs)
                    else:
                        cur_node = None
                elif cache is not None:
                    cache[fullname] = cur_node

        return cur_node

    def add_address_v2(self, record, do_update=False, cache=None):
        """
        Create a new AddressNode and add to the tree.

        Parameters
        ----------
        record : dict
            A dict object containing elements as follows.
            path : list of list
                Name-level pairs of address elements.
            x : float, y : float
                Coordinate values of the last address element.
            note : str (optional)
                A strin gcontaining notes, etc.
        do_update : bool
            When an address with the same name already exists,
            update it with the value of kwargs if 'do_update' is true,
            otherwise do nothing.
        cache : LRU
            A dict object to use as a cache for improving performance,
            whose keys are the address notation from the prefecture level
            and whose values are the corresponding nodes.
            If not specified or None is given, do not use the cache.

        Return
        ------
        The added node.
        """
        cur_node = self.get_root()
        address_names = [x[0] for x in record['path']]
        for i, element in enumerate(record['path']):
            fullname = ''.join(address_names[0:i + 1])
            if cache is not None:
                if fullname in cache:
                    cur_node = cache[fullname]
                    continue
                else:
                    logger.debug("Cache miss: '{}'".format(fullname))

            name, level = element
            name_index = itaiji_converter.standardize(name)
            node = cur_node.get_child(name_index)
            v = {'name': name, 'x': record['x'], 'y': record['y'],
                 'level': level, 'note': record.get('note', None), }
            
            if not node:
                new_node = AddressNode(**v)
                cur_node.add_child(new_node)
                cur_node = new_node
            else:
                cur_node = node
                if i == len(address_names) - 1:
                    if do_update:
                        cur_node.set_attributes(**v)
                    else:
                        cur_node = None
                elif cache is not None:
                    cache[fullname] = cur_node

        return cur_node

    def create_trie_index(self):
        """
        Create the TRIE index from the tree.
        """
        self.index_table = {}
        logger.debug("Collecting labels for the trie index...")
        self._get_index_table()

        logger.debug("Building Trie...")
        self.trie = AddressTrie(self.trie_path, self.index_table)
        self.trie.save()

        self._set_index_table()

    def _get_index_table(self):
        """
        Collect the names of all address elements
        to be registered in the TRIE index.
        The collected notations will be stored in `tree.index_table`.

        Generates notations that describe everything from the name of
        the prefecture to the name of the oaza without abbreviation,
        notations that omit the name of the prefecture, or notations
        that omit the name of the prefecture and the city.
        """
        session = self.get_session()

        # Build temporary lookup table
        logger.debug("Building temporary lookup table..")
        tmp_id_name_table = {}
        for node in session.query(
            AddressNode.id, AddressNode.name, AddressNode.parent_id).filter(
                AddressNode.level <= AddressLevel.OAZA):
            tmp_id_name_table[node.id] = node

        logger.debug("  {} records found.".format(len(tmp_id_name_table)))

        # Create index_table
        self.index_table = {}
        for k, v in tmp_id_name_table.items():
            node_prefixes = []
            cur_node = v
            while True:
                node_prefixes.insert(0, cur_node.name)
                if cur_node.parent_id < 0:
                    break

                if cur_node.parent_id not in tmp_id_name_table:
                    raise RuntimeError(
                        ('The parent_id:{} of node:{} is not'.format(
                            cur_node.parent_id, cur_node),
                         ' in the tmp_id_table'))

                cur_node = tmp_id_name_table[cur_node.parent_id]

            for i in range(len(node_prefixes)):
                label = ''.join(node_prefixes[i:])
                label_standardized = itaiji_converter.standardize(label)
                if label_standardized in self.index_table:
                    self.index_table[label_standardized].append(v.id)
                else:
                    self.index_table[label_standardized] = [v.id]

    def _set_index_table(self):
        """
        Map all the id of the TRIE index (TRIE id) to the node id.

        Collect notations recursively the names of all address elements
        which was registered in the TRIE index, retrieve
        the id of each notations in the TRIE index,
        then add the TrieNode to the database that maps
        the TRIE id to the node id.
        """

        logger.debug("Creating mapping table from trie_id:node_id")
        session = self.get_session()
        logger.debug("  Deleting old TrieNode table...")
        session.query(TrieNode).delete()
        logger.debug("  Dropping index...")
        try:
            session.execute("DROP INDEX ix_trienode_trie_id")
        except OperationalError:
            logger.debug("    the index does not exist. (ignored)")

        logger.debug("  Adding mapping records...")
        for k, node_id_list in self.index_table.items():
            trie_id = self.trie.get_id(k)
            for node_id in node_id_list:
                tn = TrieNode(trie_id=trie_id, node_id=node_id)
                session.add(tn)

        logger.debug("  Creating index on trienode.trie_id ...")
        trienode_trie_id_index = Index(
            'ix_trienode_trie_id', TrieNode.trie_id)
        try:
            trienode_trie_id_index.create(self.engine)
        except OperationalError:
            logger.debug("  the index already exists. (ignored)")

        session.commit()
        logger.debug("  done.")

    def save_all(self):
        """
        Save all AddressNode in the tree to the database.
        """
        session = self.get_session()
        logger.debug("Starting save full tree (recursive)...")
        self.get_root().save_recursive(session)
        session.commit()
        logger.debug("Finished save tree.")

    def read_file(self, path, do_update=False):
        """
        Add AddressNodes from a text file.
        See 'data/test.txt' for the format of the text file.

        Parameters
        ----------
        path : str
            Text file path.
        do_update : bool (default=False)
            When an address with the same name already exists,
            update it with the value of the new data if 'do_update' is true,
            otherwise do nothing.
        """
        logger.debug("Starting read_file...")
        with open(path, 'r', encoding='utf-8',
                  errors='backslashreplace') as f:
            self.read_stream(f, do_update=do_update)

    def read_stream(self, fp, do_update=False):
        """
        Add AddressNodes from a stream.

        Parameters
        ----------
        fp : io.TextIOBase
            Text stream.
        do_update : bool (default=False)
            When an address with the same name already exists,
            update it with the value of the new data if 'do_update' is true,
            otherwise do nothing.
        """
        nread = 0
        stocked = []
        prev_names = None
        cache = LRU(maxsize=512)

        while True:
            try:
                line = fp.readline()
            except UnicodeDecodeError as e:
                logger.error("Decode error at the next line of {}".format(
                    prev_names))
                exit(1)

            if not line:
                break

            args = line.rstrip().split(',')
            names = args[0:-3]
            lon, lat, level = args[-3:]
            try:
                lon = float(lon)
            except ValueError:
                lon = None

            try:
                lat = float(lat)
            except ValueError:
                lat = None

            try:
                level = int(level)
            except ValueError:
                level = None

            if prev_names == names:
                logger.debug("Skipping '{}".format(prev_names))
                continue

            prev_names = names

            node = self.add_address(
                names, do_update, cache=cache,
                x=lon, y=lat, level=level)
            nread += 1
            if nread % 1000 == 0:
                logger.info("- read {} lines.".format(nread))

            if node is None:
                # The node exists and not updated.
                continue

            stocked.append(node)
            if len(stocked) > 10000:
                logger.debug("Inserting into the database... ({} - {})".format(
                    stocked[0].get_fullname(), stocked[-1].get_fullname()))
                session = self.get_session()
                for node in stocked:
                    session.add(node)

                session.commit()
                stocked.clear()

        logger.debug("Finished reading the stream.")
        if len(stocked) > 0:
            logger.debug("Inserting into the database... ({} - {})".format(
                stocked[0].get_fullname(), stocked[-1].get_fullname()))
            session = self.get_session()
            for node in stocked:
                session.add(node)

            session.commit()

        logger.debug("Done.")

    def read_stream_v2(self, fp, do_update=False):
        """
        Add AddressNodes from a JSONL stream.

        Parameters
        ----------
        fp : io.TextIOBase
            Text stream.
        do_update : bool (default=False)
            When an address with the same name already exists,
            update it with the value of the new data if 'do_update' is true,
            otherwise do nothing.
        """
        nread = 0
        stocked = []
        prev_path = None
        cache = LRU(maxsize=512)

        while True:
            try:
                line = fp.readline()
            except UnicodeDecodeError as e:
                logger.error("Decode error at the next line of {}".format(
                    prev_names))
                exit(1)

            if not line:
                break

            record = json.loads(line.rstrip())
            path = record['path']

            if prev_path == path:
                logger.debug("Skipping '{}".format(prev_path))
                continue

            prev_path = path

            node = self.add_address_v2(record, do_update, cache=cache)

            nread += 1
            if nread % 1000 == 0:
                logger.info("- read {} lines.".format(nread))

            if node is None:
                # The node exists and not updated.
                continue

            stocked.append(node)
            if len(stocked) > 10000:
                logger.debug("Inserting into the database... ({} - {})".format(
                    stocked[0].get_fullname(), stocked[-1].get_fullname()))
                session = self.get_session()
                for node in stocked:
                    session.add(node)

                session.commit()
                stocked.clear()

        logger.debug("Finished reading the stream.")
        if len(stocked) > 0:
            logger.debug("Inserting into the database... ({} - {})".format(
                stocked[0].get_fullname(), stocked[-1].get_fullname()))
            session = self.get_session()
            for node in stocked:
                session.add(node)

            session.commit()

        logger.debug("Done.")

    def drop_indexes(self):
        """
        Drop indexes to improve the speed of bulk insertion.
        - ix_node_parent_id ON node (parent_id)
        - ix_trienode_trie_id ON trienode (trie_id)
        """
        logger.debug("Dropping indexes...")
        session = self.get_session()
        session.execute("DROP INDEX ix_node_parent_id")
        logger.debug("  done.")

    def create_tree_index(self):
        """
        Add index later that were not initially defined.
        - ix_node_parent_id ON node (parent_id)
        """
        logger.debug("Creating index on node.parent_id ...")
        node_parent_id_index = Index(
            'ix_node_parent_id', AddressNode.parent_id)
        try:
            node_parent_id_index.create(self.engine)
        except OperationalError:
            logger.warning("  the index already exists. (ignored)")

        logger.debug("  done.")

    def search_by_tree(self, address_names):
        """
        Get the corresponding node id from the list of address element names,
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
        The last matched node.
        """
        cur_node = self.get_root()
        for name in address_names:
            name_index = itaiji_converter.standardize(name)
            node = cur_node.get_child(name_index)
            if not node:
                break
            else:
                cur_node = node

        return cur_node

    def search_by_trie(self, query: str, best_only=True):
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
        best_only : bool (option, default=True)
            If true, get the best candidates will be returned.

        Return
        ------
        A dict object whose key is a node id
        and whose value is a list of node and substrings
        that match the query.
        """
        index = itaiji_converter.standardize(query)
        candidates = self.trie.common_prefixes(index)
        results = {}
        max_len = 0

        session = self.get_session()
        for k, id in candidates.items():
            trienodes = session.query(TrieNode).filter_by(trie_id=id).all()
            offset = len(k)
            rest_index = index[offset:]
            for trienode in trienodes:
                node = trienode.node
                results_by_node = node.search_recursive(rest_index, session)
                for cand in results_by_node:
                    _len = offset + len(cand[1])
                    if best_only:
                        if _len > max_len:
                            results = {}
                            max_len = _len

                        if _len == max_len and cand[0].id not in results:
                            results[cand[0].id] = [cand[0], k + cand[1]]

                    else:
                        results[cand[0].id] = [cand[0], k + cand[1]]
                        max_len = _len if _len > max_len else max_len

        return results

    def search(self, query: str, **kwargs):
        """
        Searches for address nodes corresponding to an address notation
        and returns the matching substring and a list of nodes.

        Note that the matched string in the "search_by_trie" result is
        the standardized one, and the substring in the "search" result
        is the unstandardized one.

        Parameters
        ----------
        query : str
            An address notation to be searched.

        Return
        ------
        A list of AddressNode and matched substring pairs.
        """
        results = self.search_by_trie(query, **kwargs)

        values = sorted(results.values(), reverse=True,
                        key=lambda v: len(v[1]))

        matched_substring = {}
        for v in values:
            if v[1] in matched_substring:
                matched = matched_substring[v[1]]
            else:
                matched = self._get_matched_substring(query, v[1])
                matched_substring[v[1]] = matched

            v[1] = matched

        return values

    def _get_matched_substring(self, query, matched):
        """
        From the substring matched standardized string,
        recover the corresponding substring of the original search string.
        
        Parameters
        ----------
        query : str
            The original search string.
        matchd : str
            The substring matched standardized string.

        Return
        ------
        The recovered substring.
        """
        l_result = len(matched)
        pos = l_result if l_result <= len(query) else len(query)

        while True:
            substr = query[0:pos]
            standardized = itaiji_converter.standardize(substr)
            l_standardized = len(standardized)
            if l_standardized == l_result:
                matched = substr
                return substr

            if l_standardized < l_result:
                pos += 1
            else:
                pos -= 1
