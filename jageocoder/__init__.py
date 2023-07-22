"""
A Python module for Japanese-address geocoding.


Note
----
Before using this module, install address-dictionary
from the Web as follows:

    $ python -m jageocoder install-dictionary

Example
-------
You can get the latitude and longitude from a Japanese address by
running the following steps.

    >>> import jageocoder
    >>> jageocoder.init()
    >>> jageocoder.searchNode('<Japanese-address>')
"""

__version__ = '2.0.3rc1'  # The package version
__dictionary_version__ = '20230405'  # Compatible dictionary version
__author__ = 'Takeshi Sagara <sagara@info-proto.com>'

__all__ = [
    'init',
    'free',
    'is_initialized',
    'set_search_config',
    'get_search_config',
    'get_db_dir',
    'get_module_tree',
    'download_dictionary',
    'install_dictionary',
    'uninstall_dictionary',
    'create_trie_index',
    'search',
    'searchNode',
    'reverse',
    'version',
    'dictionary_version',
    'installed_dictionary_version',
    'instaleld_dictionary_readme',
]

from jageocoder.module import init, free, is_initialized,\
    get_db_dir, set_search_config, get_search_config,\
    get_module_tree, download_dictionary, install_dictionary,\
    uninstall_dictionary, create_trie_index,\
    search, searchNode, reverse, version, dictionary_version,\
    installed_dictionary_version, installed_dictionary_readme  # noqa: F401
