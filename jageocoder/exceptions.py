"""
Custom exceptions.
"""


class JageocoderError(RuntimeError):
    """
    Custom exception classes sent out by jageocoder module.
    """
    pass


class AddressLevelError(RuntimeError):
    """
    Custom exception classes sent out by jageocoder.address submodule.
    """
    pass


class AddressNodeError(RuntimeError):
    """
    Custom exception classes sent out by jageocoder.node submodule.
    """
    pass


class AddressTreeException(RuntimeError):
    """
    Custom exception classes sent out by jageocoder.tree submodule.
    """
    pass


class AddressTrieError(RuntimeError):
    """
    Custom exception classes sent out by jageocoder.trie submodule.
    """
    pass
