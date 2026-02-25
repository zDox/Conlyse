import importlib
import pkgutil

def _load_all_versions():
    # iterate over subpackages like v208, v209, ...
    for finder, name, ispkg in pkgutil.iter_modules(__path__):
        if not ispkg:
            continue  # ignore stray files

        version_pkg_name = f"{__name__}.{name}"
        version_pkg = importlib.import_module(version_pkg_name)

        # now import every module inside that version package
        for _, modname, _ in pkgutil.iter_modules(version_pkg.__path__):
            full_module_name = f"{version_pkg_name}.{modname}"
            importlib.import_module(full_module_name)

_load_all_versions()
del _load_all_versions