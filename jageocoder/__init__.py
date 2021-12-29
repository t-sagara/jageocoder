"""
A Python module for Japanese-address geocoding.


Note
----
Before using this module, install address-dictionary from the Web
as follows:

    $ python -m jageocoder install-dictionary

Example
-------
You can get the latitude and longitude from a Japanese address by
running the following steps.

    >>> import jageocoder
    >>> jageocoder.init()
    >>> jageocoder.searchNode('<Japanese-address>')
"""

__version__ = '1.1.0'  # The package version
__dictionary_version__ = '20211229'  # Compatible dictionary version
__author__ = 'Takeshi Sagara <sagara@info-proto.com>'

__all__ = [
    'init',
    'is_initialized',
    'get_db_dir',
    'get_module_tree',
    'download_dictionary',
    'install_dictionary',
    'uninstall_dictionary',
    'upgrade_dictionary',
    'create_trie_index',
    'search',
    'searchNode',
    'reverse',
    'version',
    'dictionary_version'
]

from jageocoder.module import init, is_initialized, get_db_dir,\
    get_module_tree, download_dictionary, install_dictionary,\
    uninstall_dictionary, upgrade_dictionary, create_trie_index,\
    search, searchNode, reverse, version, dictionary_version
