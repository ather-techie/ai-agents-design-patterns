"""ReAct pattern package marker.

Note: this directory (``07-react``) is not importable as a normal package — the
name starts with a digit and contains a hyphen. Load ``pattern.py`` by path via
:func:`shared.loader.load_pattern_module` when you need it from another process
(see ``bench/compare.py`` and the tests).
"""
