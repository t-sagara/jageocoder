class NoIndexError(Exception):
    """
    Exception when an index-based search is attempted
    on an attribute with no index generated.
    """
    pass
