from collections import OrderedDict
import json
from logging import getLogger
import os
import site
import sys
from typing import Optional

from sqlalchemy import Index
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm.exc import NoResultFound
from sqlalchemy import create_engine
from sqlalchemy.exc import OperationalError

from jageocoder.address import AddressLevel
from jageocoder.base import Base
from jageocoder.itaiji import converter as itaiji_converter
from jageocoder.node import AddressNode
from jageocoder.trie import AddressTrie, TrieNode

logger = getLogger(__name__)


class AddressTreeException(RuntimeError):
    """
    Custom exception classes sent out by AddressTree submodule.
    """
    pass


def get_db_dir(mode: Optional[str] = 'r') -> str:
    """
    Get the database directory.

    Parameters
    ----------
    mode: str, optional(default='r')
        Specifies the mode for searching the database directory.
        If 'a' or 'w' is set, search a writable directory.
        If 'r' is set, search a database file that already exists.

    Return
    ------
    The path to the database directory.
    If no suitable directory is found, raise an AddressTreeException.

    Notes
    -----
    This method searches a directory in the following order of priority.
    - 'JAGEOCODER_DB_DIR' environment variable
    - '(sys.prefix)/jageocoder/db/'
    - '(site.USER_BASE)/jageocoder/db/'
    """
    if mode not in ('a', 'w', 'r'):
        raise AddressTreeException(
            'Invalid mode value. Specify one of "a", "w", or "r".')

    db_dirs = []
    if 'JAGEOCODER_DB_DIR' in os.environ:
        db_dirs.append(os.environ['JAGEOCODER_DB_DIR'])

    db_dirs += [
        os.path.join(sys.prefix, 'jageocoder/db/'),
        os.path.join(site.USER_BASE, 'jageocoder/db/'),
    ]

    for db_dir in db_dirs:
        path = os.path.join(db_dir, 'address.db')
        if os.path.exists(path):
            return db_dir

        if mode == 'r':
            continue

        try:
            os.makedirs(db_dir, mode=0o777, exist_ok=True)
            fp = open(path, 'a')
            fp.close()
            return db_dir
        except FileNotFoundError:
            continue

    return None


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


class AddressTree(object):
    """
    The address-tree structure.

    Attributes
    ----------
    db_path: str
        Path to the sqlite3 database file.
    dsn: str
        RFC-1738 based database-url, so called "data source name".
    trie_path: str
        Path to the TRIE index file.
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
    mode: str
        The mode in which this tree was opened.
    """

    def __init__(self, dsn=None, trie_path=None, db_dir=None,
                 mode='a', debug=False):
        """
        The initializer

        Parameters
        ----------
        dsn: str, optional
            Data Source Name of the database.
        trie_path: str, optional
            File path to save the TRIE index.
        db_dir: str, optional
            The database directory.
            If dsn and trie_path are omitted and db_dir is set,
            'address.db' and 'address.trie' under this directory will be used.
        mode: str, optional(default='a')
            Specifies the mode for opening the database.
            - In the case of 'a', if the database already exists,
              use it. Otherwize create a new one.
            - In the case of 'w', if the database already exists,
              delete it first. Then create a new one.
            - In the case of 'r', if the database already exists,
              use it. Otherwise raise a JageocoderError exception.
        debug: bool, Optional(default=False)
            Debugging flag.
        """
        # Set default values
        self.mode = mode
        if db_dir is None:
            db_dir = get_db_dir(mode)
        else:
            db_dir = os.path.abspath(db_dir)

        default_dsn = 'sqlite:///' + os.path.join(db_dir, 'address.db')
        default_trie_path = os.path.join(db_dir, 'address.trie')

        self.dsn = dsn if dsn else default_dsn
        self.db_path = self.dsn[len('sqlite:///'):]
        self.trie_path = trie_path if trie_path else default_trie_path

        # Options
        self.debug = debug

        # Clear database?
        if self.mode == 'w':
            if os.path.exists(self.db_path):
                os.remove(self.db_path)

            if os.path.exists(self.trie_path):
                os.remove(self.trie_path)

        # Database connection
        try:
            self.engine = create_engine(self.dsn, echo=self.debug)
            self.conn = self.engine.connect()
            _session = sessionmaker()
            _session.configure(bind=self.engine)
            self.session = _session()
        except Exception as e:
            logger.error(e)
            exit(1)

        self.root = None
        self.trie = AddressTrie(self.trie_path)

    def close(self):
        if self.session:
            self.session.close()

        if self.engine:
            self.engine.dispose()
            del self.engine
            self.engine = None

    def __not_in_readonly_mode(self):
        if self.mode == 'r':
            raise AddressTreeException(
                'This method is not available in read-only mode.')

    def create_db(self):
        """
        Create database and tables.
        """
        self.__not_in_readonly_mode()
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
        -------
        The AddressNode object.
        """
        if self.root:
            return self.root

        # Try to get root from the database
        try:
            self.root = self.session.query(
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
        self.__not_in_readonly_mode()
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
        self.__not_in_readonly_mode()
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
        self.__not_in_readonly_mode()
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
        # Build temporary lookup table
        logger.debug("Building temporary lookup table..")
        tmp_id_name_table = {}
        for node in self.session.query(
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

        self.session.commit()

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
        logger.debug("  Deleting old TrieNode table...")
        self.session.query(TrieNode).delete()
        logger.debug("  Dropping index...")
        try:
            self.session.execute("DROP INDEX ix_trienode_trie_id")
        except OperationalError:
            logger.debug("    the index does not exist. (ignored)")

        logger.debug("  Adding mapping records...")
        for k, node_id_list in self.index_table.items():
            trie_id = self.trie.get_id(k)
            for node_id in node_id_list:
                tn = TrieNode(trie_id=trie_id, node_id=node_id)
                self.session.add(tn)

        logger.debug("  Creating index on trienode.trie_id ...")
        trienode_trie_id_index = Index(
            'ix_trienode_trie_id', TrieNode.trie_id)
        try:
            trienode_trie_id_index.create(self.engine)
        except OperationalError:
            logger.debug("  the index already exists. (ignored)")

        self.session.commit()
        logger.debug("  done.")

    def save_all(self):
        """
        Save all AddressNode in the tree to the database.
        """
        self.__not_in_readonly_mode()
        logger.debug("Starting save full tree (recursive)...")
        self.get_root().save_recursive(self.session)
        self.session.commit()
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
        raise AddressTreeException(
            'This method is not available in read-only mode.')
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
        self.__not_in_readonly_mode()
        nread = 0
        stocked = []
        prev_names = None
        cache = LRU(maxsize=512)

        while True:
            try:
                line = fp.readline()
            except UnicodeDecodeError:
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
                for node in stocked:
                    self.session.add(node)

                self.session.commit()
                stocked.clear()

        logger.debug("Finished reading the stream.")
        if len(stocked) > 0:
            logger.debug("Inserting into the database... ({} - {})".format(
                stocked[0].get_fullname(), stocked[-1].get_fullname()))
            for node in stocked:
                self.session.add(node)

            self.session.commit()

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
        self.__not_in_readonly_mode()
        nread = 0
        stocked = []
        prev_path = None
        cache = LRU(maxsize=512)

        while True:
            try:
                line = fp.readline()
            except UnicodeDecodeError:
                logger.error("Decode error at the next line of {}".format(
                    prev_path))
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
                for node in stocked:
                    self.session.add(node)

                self.session.commit()
                stocked.clear()

        logger.debug("Finished reading the stream.")
        if len(stocked) > 0:
            logger.debug("Inserting into the database... ({} - {})".format(
                stocked[0].get_fullname(), stocked[-1].get_fullname()))
            for node in stocked:
                self.session.add(node)

            self.session.commit()

        logger.debug("Done.")

    def drop_indexes(self):
        """
        Drop indexes to improve the speed of bulk insertion.
        - ix_node_parent_id ON node (parent_id)
        - ix_trienode_trie_id ON trienode (trie_id)
        """
        self.__not_in_readonly_mode()
        logger.debug("Dropping indexes...")
        self.session.execute("DROP INDEX ix_node_parent_id")
        logger.debug("  done.")

    def create_tree_index(self):
        """
        Add index later that were not initially defined.
        - ix_node_parent_id ON node (parent_id)
        """
        self.__not_in_readonly_mode()
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

        for k, id in candidates.items():
            trienodes = self.session.query(
                TrieNode).filter_by(trie_id=id).all()
            offset = len(k)
            rest_index = index[offset:]
            for trienode in trienodes:
                node = trienode.node
                results_by_node = node.search_recursive(
                    rest_index, self.session)
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
