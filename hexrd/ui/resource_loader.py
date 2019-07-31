try:
    import importlib.resources as importlib_resources
except ImportError:
    # Try backported to PY<37 `importlib_resources`.
    import importlib_resources


def load_resource(module, name, binary=False):
    """This will return a string of a resource's contents"""
    if binary:
        return importlib_resources.read_binary(module, name)

    return importlib_resources.read_text(module, name)
