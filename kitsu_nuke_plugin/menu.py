"""Nuke GUI startup hook: adds the "Kitsu" menu and registers the panel.

Nuke executes this file automatically, after init.py, for every folder on
its plugin path — but only in GUI sessions, which is exactly right for a
menu and a panel (a batch render should never build either).

Everything here is deliberately lazy. The menu commands are strings, so
the panel, Qt and the vendored `gazu` are only imported when an entry is
actually clicked; the panel widget itself is registered as a string too
(see menu_actions.PANEL_WIDGET), which nukescripts evaluates only when a
panel is created. A broken install can therefore never stop Nuke from
starting — at worst a menu entry reports the problem in the Script
Editor when used.

The Nuke counterpart of the Maya port's "Kitsu/Zou" main-menu plug-in and
the Houdini port's "Kitsu" shelf. Named plain "Kitsu" rather than
"Kitsu/Zou" like the other ports, because Nuke reads a slash in a menu
name as a path separator — "Kitsu/Zou" would nest the commands one level
deeper, under a pointless "Zou" submenu.
"""

import os

import nuke

from kitsu_nuke_plugin import menu_actions

# Absolute so the icon resolves regardless of whether this plugin's own
# folder happens to be on Nuke's icon search path.
_ICON = os.path.join(
    os.path.dirname(os.path.abspath(__file__)), "icons", "kitsu_nuke_plugin.png"
).replace("\\", "/")

menu_actions.register_panel()

_menu = nuke.menu("Nuke").addMenu("Kitsu", icon=_ICON)
_menu.addCommand(
    "Open Kitsu Panel",
    "from kitsu_nuke_plugin import menu_actions; menu_actions.open_panel()",
    icon=_ICON,
)
_menu.addCommand(
    "Publish Capture",
    "from kitsu_nuke_plugin import menu_actions; menu_actions.publish_capture()",
    icon=_ICON,
)
