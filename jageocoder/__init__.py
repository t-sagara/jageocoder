"""
jageocoder is a Python module for the Japanese-address geocoding.
"""

__version__ = '0.3.0rc3'  # The package version
__dictionary_version__ = '20211112'  # Compatible dictionary version
__author__ = 'Takeshi Sagara'

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
]

from jageocoder.module import init, is_initialized, get_db_dir,\
    get_module_tree, download_dictionary, install_dictionary,\
    uninstall_dictionary, upgrade_dictionary, create_trie_index,\
    search, searchNode
