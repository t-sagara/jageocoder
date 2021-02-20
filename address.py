import copy
import logging
import os
import re

import marisa_trie
from sqlalchemy import Column, ForeignKey, Integer, Float, String, Text
from sqlalchemy import or_
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import backref, relationship, sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import create_engine

from itaiji import converter as itaiji_converter

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
            return [[self, 0]]

        conds = []
        i = 0
        while i < len(index):
            if index[i] == '-':
                substr = index[0:i] + '%'
                conds.append(self.__class__.name_index.like(substr))
                logging.debug("  conds: name_index LIKE '{}'".format(
                    substr))
            elif '0' <= index[i] and index[i] <= '9':
                for j in range(i, len(index)):
                    if index[j] == '.':
                        break

                substr = index[0:j+1]
                conds.append(self.__class__.name_index == substr)
                logging.debug("  conds: name_index == '{}'".format(
                    substr))
                i = j
            else:
                substr = index[0:i+1]
                conds.append(self.__class__.name_index == substr)
                logging.debug("  conds: name_index == '{}'".format(
                    substr))

            i += 1

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
                    candidates.append([cand[0], cand[1] + offset])
                    
            elif re_index is not None:
                m = re_index.match(child.name_index)
                if not m:
                    continue

                offset = len(m.group(0))
                rest_index = index[hyphen_pos + 1:]
                logging.debug("child:{} match {} chars".format(child, offset))
                for cand in child.search_recursive(rest_index, session):
                    candidates.append([cand[0], cand[1] + offset])

        if len(candidates) == 0:
            candidates = [[self, 0]]

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
            for i in range(len(node_prefixes)):
                label = ''.join(node_prefixes[i:])
                tree.index_table[label] = True

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
            for i in range(len(node_prefixes)):
                label = ''.join(node_prefixes[i:])
                if label in tree.index_table:
                    if self.id is None:
                        raise RuntimeError("Node '{}' is not assigned a valid id (Save the tree first).".format(self))
                    
                    tn = TrieNode(
                        trie_id=tree.index_table[label],
                        node_id=self.id)
                    session.add(tn)

        for c in self.children:
            c.set_index_recursive(tree, node_prefixes, session)

    def save_recursive(self, session):
        session.add(self)
        for c in self.children:
            c.save_recursive(session)

    def __str__(self):
        return '{}:{}'.format(self.id, self.name)

        return '[{}:{}({},{}){}({})]'.format(
            self.id, self.name, self.x, self.y, self.level, str(self.note))

    def __repr__(self):
        r = []
        cur_node = self
        while cur_node.parent:
            r.append(str(cur_node))
            cur_node = cur_node.parent

        return '<'.join(r)


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

    # ref: https://qiita.com/msrks/items/15144746ff4f7aced4b5

    def __init__(self, *args, **kwargs):
        dsn = kwargs.get('dsn', 'sqlite:///address.db')
        self.debug = kwargs.get('debug', False)
        self.engine = create_engine(dsn, echo=self.debug)
        self.Session = sessionmaker()
        self.Session.configure(bind=self.engine)
        self.root = None

        self.trie_path = kwargs.get('trie', 'address.trie')
        self.trie = AddressTrie(self.trie_path)

        self.conn = self.engine.connect()
        self.session = self.Session()

    def create_db(self):
        Base.metadata.create_all(self.engine)

    def get_session(self):
        return self.session

    def get_root(self):
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

    def create_trie_index(self):

        self.index_table = {}
        logging.debug("Collecting labels for the trie index...")
        self.get_root().get_index_recursive(self, '')

        logging.debug("Building Trie...")
        self.trie = AddressTrie(self.trie_path, self.index_table)
        self.trie.save()

        logging.debug("Creating table of label:trie_id...")
        for k in self.index_table.keys():
            self.index_table[k] = self.trie.get_id(k)

        logging.debug("Creating mapping from trie_id:node_id...")
        session = self.get_session()
        session.query(TrieNode).delete()
        self.get_root().set_index_recursive(self, None, session)
        session.commit()

    def save(self):
        logging.debug("Starting save tree (recursive)...")
        session = self.get_session()
        self.get_root().save_recursive(session)
        session.commit()
        logging.debug("Finished save tree.")

    def read_file(self, path):
        logging.debug("Starting read_file...")
        nread = 0
        with open(path, 'r', encoding='utf-8') as f:
            while True:
                line = f.readline()
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

                self.add_address(names, x=lon, y=lat, level=level)

                nread += 1
                if nread % 1000 == 0:
                    logging.debug("- read {} lines.".format(nread))

        logging.debug("Finished read_file.")
                    

    def search(self, address_names):
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
        results = []

        session = self.get_session()
        for k, id in candidates.items():
            trienodes = session.query(TrieNode).filter_by(trie_id=id).all()
            offset = len(k)
            rest_index = index[offset:]
            for trienode in trienodes:
                node = trienode.node
                for cand in node.search_recursive(rest_index, session):
                    results.append([cand[0], cand[1] + offset])

        return results

if __name__ == '__main__':
    trie = AddressTrie('test.trie')
    for k, v in {'青森県': 1, '青森県青森市': 2}.items():
        trie.add(k)

    trie.save()

    print(trie.common_prefixes('青森県青森市中央１'))
    print(trie.predict_prefixes('青'))
