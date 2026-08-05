"""Nuke startup hook: makes the `kitsu_nuke_plugin` Python package importable.

Nuke executes this file automatically for every folder on its plugin
path (see the installer, which adds this folder to it from ~/.nuke/init.py),
in both GUI and terminal/render sessions — unlike menu.py, which only runs
in the GUI. Nothing is registered here: the menu and the panel are set up
in menu.py, so a batch render never pays for either.

The package deliberately lives in a `python/` subfolder rather than
directly in this one. Nuke puts every plugin-path folder on `sys.path`,
so anything sitting next to this file would become importable under its
own bare name — a `panel.py` or `settings.py` at this level could shadow
another tool's module of the same name. Only `python/` (which contains
nothing but the package folder) is added to `sys.path` instead, so the
plugin's modules are reachable exclusively as `kitsu_nuke_plugin.*`.
"""

import os
import sys

_PYTHON_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "python")

if _PYTHON_DIR in sys.path:
    sys.path.remove(_PYTHON_DIR)
# Inserted first so that this copy of the package always wins over an
# older install left on PYTHONPATH or in Nuke's site-packages.
sys.path.insert(0, _PYTHON_DIR)
