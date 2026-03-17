import importlib
import pkgutil

def _load_all_versions():
    # iterate over subpackages like v208, v209, ...
    for finder, name, ispkg in pkgutil.iter_modules(__path__):
        if not ispkg:
            continue  # ignore stray files

        version_pkg_name = f"{__name__}.{name}"
        version_pkg = importlib.import_module(version_pkg_name)

        # Import every module/package inside that version package recursively.
        for module_info in pkgutil.walk_packages(version_pkg.__path__, prefix=f"{version_pkg_name}."):
            importlib.import_module(module_info.name)

_load_all_versions()
del _load_all_versions