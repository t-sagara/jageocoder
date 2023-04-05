from logging import getLogger
import os

import marisa_trie
from PortableTab import BaseTable

from jageocoder.exceptions import AddressTrieError

logger = getLogger(__name__)


class TrieNode(BaseTable):
    """
    The mapping-table of TRIE id and Node id. Stored in 'trienode' table.

    Attributes
    ----------
    id : int
        The TRIE id.
    nodes : List[int]
        List of node id that corresponds to the TRIE id.

    Note
    ----
    - Some of the notations correspond to multiple address elements.
      For example, "中央区中央" exists in either 千葉市 and 相模原市,
      so TRIE id and node id correspond one-to-many.
    """

    __tablename__ = 'trienode'
    __schema__ = """
        struct TrieNode {
            id @0 :UInt32;
            nodes @1 :List(UInt32);
        }
        """
    __record_type__ = "TrieNode"


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
        self.path = str(path)  # Marisa-trie uses string path
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
        if self.trie is None:
            raise AddressTrieError((
                "The trie-index is not created."
                "Try running 'jageocoder migrate-dictinary'"))

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
        if self.trie is None:
            raise AddressTrieError('The trie-index is not created.')

        results = {}
        for p in self.trie.iterkeys(query):
            results[p] = self.trie.key_id(p)

        return results
