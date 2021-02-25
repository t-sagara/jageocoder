import copy
import logging
import os
import re

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

# ref [SQLAlchemy Tutorial](https://docs.sqlalchemy.org/en/13/orm/tutorial.html?highlight=tutorial)

Base = declarative_base()

# ref https://stackoverflow.com/questions/4896104/creating-a-tree-from-self-referential-tables-in-sqlalchemy

class AddressNode(Base):
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
        super().__init__(*args, **kwargs)
        # Basic attributes
        self.name = kwargs.get('name', '')

        # Extended attributes
        # kwargs can contains 'x', 'y', 'level' and 'note'
        self.x = kwargs.get('x', kwargs.get('lon'))
        self.y = kwargs.get('y', kwargs.get('lat'))
        self.level = kwargs.get('level')
        self.note = kwargs.get('note')

        # For indexing
        self.name_index = itaiji_converter.standardize(self.name)

        # Relations
        self.parent_id = kwargs.get('parent_id', None)

    def add_child(self, child):
        self.children.append(child)

    def add_to_parent(self, parent):
        self.parent = parent

    def get_child(self, target_name):
        for c in self.children:
            if c.name == target_name or c.name_index == target_name:
                return c

        return None

    def search_recursive(self, index, session):
        logging.debug("node:{}, index:{}".format(self, index))
        if len(index) == 0:
            return [[self, '']]

        conds = []

        if '0' <= index[0] and index[0] <= '9':
            for i in range(0, len(index)):
                if index[i] == '.':
                    break

            substr = index[0:i+1] + '%'
            conds.append(self.__class__.name_index.like(substr))
            logging.debug("  conds: name_index LIKE '{}'".format(substr))
        else:
            substr = index[0:1] + '%'
            conds.append(self.__class__.name_index.like(substr))
            logging.debug("  conds: name_index LIKE '{}'".format(substr))

        filtered_children = session.query(self.__class__).filter(
            self.__class__.parent_id == self.id, or_(*conds))
            
        if '-' in index:
            hyphen_pos = index.index('-')
            re_index = re.compile('^' + re.escape(index[0:hyphen_pos]) + '.*')
        else:
            re_index = None
            
        candidates = []
        for child in filtered_children:
            logging.debug("-> comparing; {}".format(child.name_index))

            if index.startswith(child.name_index):
                offset = len(child.name_index)
                rest_index = index[offset:]
                logging.debug("child:{} match {} chars".format(child, offset))
                for cand in child.search_recursive(rest_index, session):
                    candidates.append([cand[0], child.name_index + cand[1]])

                continue
            
            if '条' in child.name_index:
                # 札幌市など「北3条西一丁目」の「北3西1」表記対応
                alt_name_index = child.name_index.replace('条', '', 1)
                if index.startswith(alt_name_index):
                    offset = len(alt_name_index)
                    rest_index = index[offset:]
                    logging.debug("child:{} match {} chars".format(child, offset))
                    for cand in child.search_recursive(rest_index, session):
                        candidates.append([cand[0], alt_name_index + cand[1]])

                    continue
                
            if re_index is not None:
                m = re_index.match(child.name_index)
                if not m:
                    continue

                offset = len(m.group(0))
                rest_index = index[hyphen_pos + 1:]
                logging.debug("child:{} match {} chars".format(child, offset))
                for cand in child.search_recursive(rest_index, session):
                    candidates.append(
                        [cand[0], index[0:hyphen_pos+1] + cand[1]])

        if self.level == 4 and self.parent.name == '京都市':
            # 京都市の通り名対応
            for child in self.children:
                pos = index.find(child.name_index)
                if pos > 0:
                    offset = pos + len(child.name_index)
                    rest_index = index[offset:]
                    logging.debug("child:{} match {} chars".format(child, offset))
                    for cand in child.search_recursive(rest_index, session):
                        candidates.append([cand[0], index[0: offset] + cand[1]])
 
        if len(candidates) == 0:
            candidates = [[self, '']]

        logging.debug("node:{} returns {}".format(self, candidates))

        return candidates

    def get_index_recursive(self, tree, prefixes):
        node_prefixes = copy.copy(prefixes)
        if self.name == '_root_':
            node_prefixes = []
        elif self.level > 5:
            return
        else:
            node_prefixes.append(self.name_index)

            if self.level == 3:
                logging.debug("node: {} prefixes = {}".format(self, prefixes))
                
            for i in range(len(node_prefixes)):
                label = ''.join(node_prefixes[i:])
                tree.index_table[label] = True

        if self.name == '_root_' or self.level < 5:
            for c in self.children:
                c.get_index_recursive(tree, node_prefixes)

        return

    def set_index_recursive(self, tree, prefixes, session):
        node_prefixes = copy.copy(prefixes)
        if self.name == '_root_':
            node_prefixes = []
        elif self.level > 5:
            return
        else:
            node_prefixes.append(self.name_index)
            
            if self.level == 3:
                logging.debug("node: {} prefixes = {}".format(self, prefixes))
                
            for i in range(len(node_prefixes)):
                label = ''.join(node_prefixes[i:])
                if label in tree.index_table:
                    if self.id is None:
                        raise RuntimeError("Node '{}' is not assigned a valid id (Save the tree first).".format(self))
                    
                    tn = TrieNode(
                        trie_id=tree.index_table[label],
                        node_id=self.id)
                    session.add(tn)

        if self.name == '_root_' or self.level < 5:
            for c in self.children:
                c.set_index_recursive(tree, node_prefixes, session)

    def save_recursive(self, session):
        session.add(self)
        for c in self.children:
            c.save_recursive(session)

    def as_dict(self):
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
    __tablename__ = 'trienode'

    id = Column(Integer, primary_key=True)
    trie_id = Column(Integer, nullable=False)
    node_id = Column(Integer, ForeignKey('node.id'), nullable=False)

    node = relationship("AddressNode")


class AddressTrie(object):

    def __init__(self, path, words: dict = {}):
        self.path = path
        self.trie = None
        self.words = words

        if os.path.exists(path):
            self.connect()

    def connect(self):
        self.trie = marisa_trie.Trie().mmap(self.path)

    def add(self, word: str):
        self.words[word] = True

    def save(self):
        if self.trie:
            del self.trie

        if os.path.exists(self.path):
            os.remove(self.path)

        self.trie = marisa_trie.Trie(self.words.keys())
        self.trie.save(self.path)

        del self.trie
        self.connect()

    def get_id(self, query: str):
        return self.trie.key_id(query)

    def common_prefixes(self, query: str):
        results = {}
        for p in self.trie.iter_prefixes(query):
            results[p] = self.trie.key_id(p)

        return results

    def predict_prefixes(self, query: str):
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
            logging.error(e)
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
        If not set yet, (create and ) get the node from the database.

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

    def add_address(self, address_names, **kwargs):
        """
        Create a new AddressNode and add to the tree.

        Parameters
        ----------
        address_names : list of str
            A list of the parent's address name.
            For example, ["東京都","新宿区","西新宿"]
        **kwargs : properties of the new address node.
            name : str. name. ("２丁目")
            x : float. X coordinate or longitude. (139.69175)
            y : float. Y coordinate or latitude. (35.689472)
            level : int. Address level (1: pref, 3: city, 5: oaza, ...)
            note : str. Note.
        """
        cur_node = self.get_root()
        for name in address_names:
            node = cur_node.get_child(name)
            if not node:
                kwargs.update({'name': name, 'parent': cur_node})
                new_node = AddressNode(**kwargs)
                cur_node.add_child(new_node)
                cur_node = new_node
            else:
                cur_node = node

        return cur_node

    def create_trie_index(self):
        """
        Create the TRIE index from the tree.
        """
        self.index_table = {}
        logging.debug("Collecting labels for the trie index...")
        self._get_index_table()
        # self.get_root().get_index_recursive(self, '')

        logging.debug("Building Trie...")
        self.trie = AddressTrie(self.trie_path, self.index_table)
        self.trie.save()

        self._set_index_table()

    def _get_index_table(self):
        session = self.get_session()

        # Build temporary lookup table
        logging.debug("Building temporary lookup table..")
        tmp_id_name_table = {}
        for node in session.query(
            AddressNode.id, AddressNode.name, AddressNode.parent_id).filter(
                AddressNode.level <= 5):
            tmp_id_name_table[node.id] = node

        logging.debug("  {} records found.".format(len(tmp_id_name_table)))

        # Create index_table
        self.index_table = {}
        for k, v in tmp_id_name_table.items():
            node_prefixes = []
            cur_node = v
            while True:
                node_prefixes.insert(0, cur_node.name)
                if cur_node.parent_id < 0:
                    break
                
                cur_node = tmp_id_name_table[cur_node.parent_id]

            for i in range(len(node_prefixes)):
                label = ''.join(node_prefixes[i:])
                label_standardized = itaiji_converter.standardize(label)
                if label_standardized in self.index_table:
                    self.index_table[label_standardized].append(v.id)
                else:
                    self.index_table[label_standardized] = [v.id]

    def _set_index_table(self):
        logging.debug("Creating mapping table from trie_id:node_id")
        session = self.get_session()
        logging.debug("  Deleting old TrieNode table...")
        session.query(TrieNode).delete()
        logging.debug("  Dropping index...")
        try:
            session.execute("DROP INDEX ix_trienode_trie_id")
        except OperationalError:
            logging.debug("    the index does not exist. (ignored)")

        logging.debug("  Adding mapping records...")
        for k, node_id_list in self.index_table.items():
            trie_id = self.trie.get_id(k)
            for node_id in node_id_list:
                tn = TrieNode(trie_id=trie_id, node_id=node_id)
                session.add(tn)

        logging.debug("  Creating index on trienode.trie_id ...")
        trienode_trie_id_index = Index(
            'ix_trienode_trie_id', TrieNode.trie_id)
        try:
            trienode_trie_id_index.create(self.engine)
        except OperationalError:
            logging.warning("  the index already exists. (ignored)")

        session.commit()
        logging.debug("  done.")

    def save_all(self):
        """
        Save all AddressNode in the tree to the database.
        """
        session = self.get_session()
        logging.debug("Starting save full tree (recursive)...")
        self.get_root().save_recursive(session)
        session.commit()
        logging.debug("Finished save tree.")

    def read_file(self, path, grouping_level=4):
        logging.debug("Starting read_file...")
        with open(path, 'r', encoding='utf-8',
                  errors='backslashreplace') as f:
            self.read_stream(f, grouping_level)

    def read_stream(self, fp, grouping_level=4):
        nread = 0
        nstocked = 0
        subtree = None
        prev_names = None
        while True:
            try:
                line = fp.readline()
            except UnicodeDecodeError as e:
                logging.error("Decode error at the next line of {}".format(
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
                logging.debug("Skipping '{}".format(prev_names))
                continue

            prev_names = names
            
            node = self.add_address(names, x=lon, y=lat, level=level)
            nread += 1
            if nread % 1000 == 0:
                logging.debug("- read {} lines.".format(nread))

            nstocked += 1
            if node.level <= grouping_level:
                # Stock the previous subtree
                if subtree:
                    logging.debug("Saving subtree {}".format(subtree))
                    session = self.get_session()
                    subtree.save_recursive(session)

                    if nstocked > 100000:
                        logging.debug("  commit.")
                        session.commit()
                        nstocked = 0

                subtree = node

        logging.debug("Finished read_stream.")
        if subtree:
            logging.debug("Saving the last subtree {}".format(subtree))
            session = self.get_session()
            subtree.save_recursive(session)
            session.commit()


    def drop_indexes(self):
        """
        Drop indexes to improve INSERT speed.
        - ix_node_parent_id ON node (parent_id)
        - ix_trienode_trie_id ON trienode (trie_id)
        """
        logging.debug("Dropping indexes...")
        session = self.get_session()
        session.execute("DROP INDEX ix_node_parent_id")
        logging.debug("  done.")

    def create_tree_index(self):
        """
        Add index later that were not initially defined
        to improve INSERT speed.
        - ix_node_parent_id ON node (parent_id)
        """
        logging.debug("Creating index on node.parent_id ...")
        node_parent_id_index = Index(
            'ix_node_parent_id', AddressNode.parent_id)
        try:
            node_parent_id_index.create(self.engine)
        except OperationalError:
            logging.warning("  the index already exists. (ignored)")

        logging.debug("  done.")

    def search_by_tree(self, address_names):
        cur_node = self.get_root()
        for name in address_names:
            name_index = itaiji_converter.standardize(name)
            node = cur_node.get_child(name_index)
            if not node:
                break
            else:
                cur_node = node

        return cur_node

    def search_by_trie(self, query: str):
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
                    if _len > max_len:
                        results = {}
                        
                    if cand[0].id not in results:
                        results[cand[0].id] = [cand[0], k + cand[1]]

        return results

    def search(self, query):
        results = self.search_by_trie(query)
        if len(results) == 0:
            return {"matched": "", "candidates": []}
            
        top_result = ''
        for v in results.values():
            top_result = v[1]
            break

        l_result = len(top_result)
        matched = None
        pos = l_result if l_result <= len(query) else len(query)
        while True:
            substr = query[0:pos]
            standardized = itaiji_converter.standardize(substr)
            l_standardized = len(standardized)
            if l_standardized == l_result:
                matched = substr
                break

            if l_standardized < l_result:
                pos += 1
            else:
                pos -= 1

        return {
            "matched": matched,
            "candidates": [x[0] for x in results.values()]
        }
