from pathlib import Path
from typing import Callable, List, Optional

import marisa_trie

from .base_table import BaseTable
from .exceptions import NoIndexError
from .types import Record


class BaseIndex(object):

    def __init__(
            self,
            table: BaseTable,
    ) -> None:
        self.table = table
        self.trie_indexes = {}

    def get_trie_path(self, attr: str) -> Path:
        return self.table.get_dir() / f"{self.table.tablename}_{attr}.trie"

    def create_trie_on(
        self,
        attr: str,
        key_func: Optional[Callable] = None,
        filter_func: Optional[Callable] = None,
    ) -> None:
        """
        Create TRIE index on the specified attribute.

        Paramters
        ---------
        attr: str
            The name of target attribute.
        key_func: Callable, optional
            A function that takes the attribute value as argument
            used to generate a set of index key strings from each record.
            If not specified, the 'str' function will be used.
        filter_func: Callable, optional
            A function that takes the record as argument to determine
            if the record should be added to the index or not.
            When the function returns true (in the context of Boolean
            operation), the record will be indexed.
            If not specified, all records will be indexed.

        Notes
        -----
        - The created index is saved in the same directory as
          the page files with the file name "<attr>.trie".
        """
        def kvgen():
            # Generator function to enumerate sets of
            # attribute value and position.
            for pos, record in enumerate(self.table.get_records_by_pos(
                from_pos=0, to_pos=self.table.count_records()
            )):
                if pos == 0 and attr not in record:
                    raise ValueError(f"Field '{attr}' doesn't exist.")

                if filter_func and not filter_func(record):
                    continue

                if key_func is None:
                    strings = str(record[attr])
                else:
                    strings = key_func(record[attr])

                if isinstance(strings, str) and strings != "":
                    yield (strings, (pos,))
                else:
                    for string in strings:
                        if string != "":
                            yield (string, (pos,))

        # Create RecordTrie
        # https://marisa-trie.readthedocs.io/en/latest/tutorial.html#marisa-trie-recordtrie  # noqa: E501
        trie = marisa_trie.RecordTrie("<L", kvgen())
        path = self.get_trie_path(attr)
        trie.save(str(path))

        # Open the trie using mmap.
        self.open_trie_on(attr)

    def open_trie_on(
        self,
        attr: str
    ) -> marisa_trie.RecordTrie:
        """
        Open TRIE index on the specified attribute.

        Paramters
        ---------
        attr: str
            The name of target attribute.

        Returns
        -------
        RecordTrie
            The TRIE index.

        Notes
        -----
        - The index is mmapped from the file name "<attr>.trie",
          in the same directory as the page files.
        """
        if attr in self.trie_indexes:
            return self.trie_indexes[attr]

        path = self.get_trie_path(attr)
        if not path.exists():
            raise NoIndexError(f"Index '{path}' doesn't exist.")

        trie = marisa_trie.RecordTrie("<L").mmap(str(path))
        self.trie_indexes[attr] = trie
        return trie

    def delete_trie_on(self, attr: str) -> None:
        """
        Delete TRIE index on the specified attribute.

        Paramters
        ---------
        attr: str
            The name of target attribute.

        Notes
        -----
        - Delete any file named "<attr>.trie" in the same directory
          as the page files.
        - If the index is already loaded, unload it.
        """
        path = self.get_trie_path(attr)
        if path.exists():
            path.unlink()

        if attr in self.trie_indexes:
            del self.trie_indexes[attr]

    def search_records_on(
        self,
        attr: str,
        value: str,
        funcname: str = "get"
    ) -> List[Record]:
        """
        Search value from the table on the specified attribute.

        Paramters
        ---------
        attr: str
            The name of target attribute.
        value: str
            The target value.
        funcname: str
            The name of search method.
            - "get" searches for records that exactly match the value.
            - "prefixes" searches for records that contained in the value.
            - "keys" searches for records that containing the value.

        Returns
        -------
        List[Record]
            List of records.

        Notes
        -----
        - TRIE index must be created on the column before searching.
        - The TRIE index file will be automatically opened if it exists.
        """
        if funcname not in ("get", "prefixes", "keys"):
            raise ValueError("'func' must be 'get', 'prefixes' or 'keys'.")

        trie = self.open_trie_on(attr)
        positions = []
        if funcname == "get":
            positions = trie.get(value, [])
        elif funcname == "prefixes":
            for v in trie.prefixes(value):
                positions += trie.get(v, [])

        elif funcname == "keys":
            for v in trie.keys(value):
                positions += trie.get(v, [])

        records = []
        for pos in set([p[0] for p in positions]):
            records.append(self.table.get_record(pos))

        return records
