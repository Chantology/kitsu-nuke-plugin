"""Kitsu/Zou integration for Nuke.

Nothing is registered at package import time — the plugin's own menu.py
(one level up, executed by Nuke at GUI startup) adds the "Kitsu" menu
and registers the panel, and the panel itself is only constructed when
the user actually opens it.
"""
