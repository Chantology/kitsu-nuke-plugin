"""What the "Kitsu" menu entries actually do.

Kept out of the plugin's menu.py (which Nuke executes at GUI startup) so
that building the menu itself never imports the panel, Qt or anything
vendored: the menu is registered from strings that only import this
module when an entry is actually clicked, so a problem anywhere in the
plugin can at worst break the command that hit it, not Nuke's startup.

The Nuke counterpart of the Maya port's plug-in entry point
(kitsuMayaPlugin.py) and the Houdini port's two shelf tools.
"""

import nuke
import nukescripts

# Nuke only needs this to be unique across every panel installed in a
# session; the reverse-domain form Nuke's own panels use (uk.co.thefoundry.*)
# is a convention, not a requirement. This uses the plugin's Python package
# name instead of any one studio's domain: it's unique for the same reason
# the package is, and it stays correct for whoever deploys this.
PANEL_ID = "kitsu_nuke_plugin.KitsuPanel"
PANEL_NAME = "Kitsu"

# Evaluated by nukescripts' PyCustom_Knob only when a panel is actually
# created, which is what keeps the panel (and everything it imports) out
# of Nuke's startup path — see menu.py.
PANEL_WIDGET = "__import__('kitsu_nuke_plugin.panel', fromlist=['KitsuPanel']).KitsuPanel"


def register_panel():
    """Make the Kitsu panel available as a pane tab.

    Adds it to the "Pane" menu (so it can be added to any pane the same
    way as the Properties or Curve Editor panels) and registers it under
    PANEL_ID, which is both what open_panel() below restores and what
    Nuke itself uses to bring the panel back when it restores a saved
    layout containing one.
    """
    nukescripts.panels.registerWidgetAsPanel(PANEL_WIDGET, PANEL_NAME, PANEL_ID)


def open_panel():
    """Open the Kitsu panel as a pane tab.

    Docked next to the Properties pane when there is one (the right-hand
    column in Nuke's default layout, which is where a panel like this
    belongs), else next to the node graph, else floating. Opening it
    twice gives two tabs — the same as Nuke's own panels, which have no
    "raise the existing one" API to use instead.
    """
    panel = nukescripts.panels.restorePanel(PANEL_ID)
    if panel is None:
        raise RuntimeError(
            "The Kitsu panel isn't registered — check the Script Editor for "
            "errors from this plugin's menu.py at Nuke startup."
        )

    for pane_name in ("Properties.1", "DAG.1", "Viewer.1"):
        pane = nuke.getPaneFor(pane_name)
        if pane is not None:
            return panel.addToPane(pane)

    # No pane to dock into (a stripped-down layout): float it instead of
    # silently doing nothing — restorePanel() has already built the
    # widget by this point either way.
    panel.show()
    return panel


def publish_capture():
    """Export a full-range H.264 MP4 of what the Viewer is showing and
    publish it to Kitsu as a new revision on the detected task."""
    from kitsu_nuke_plugin import panel as panel_module
    from kitsu_nuke_plugin import publish_capture as publish_capture_module

    active_panel = panel_module.get_active_panel()
    try:
        publish_capture_module.ensure_ready(active_panel)
    except publish_capture_module.PublishCaptureError as exc:
        nuke.message(str(exc))
        return

    try:
        statuses = active_panel.session.all_task_statuses(active_panel.project)
    except Exception as exc:
        nuke.message(f"Could not load task statuses: {exc}")
        return

    from kitsu_nuke_plugin.capture_dialog import prompt_for_status_and_comment

    prompted = prompt_for_status_and_comment(statuses, parent=active_panel)
    if prompted is None:
        return  # cancelled, or no status available to select
    task_status, comment = prompted

    try:
        output_path = publish_capture_module.run(active_panel, task_status, comment)
    except publish_capture_module.PublishCaptureError as exc:
        nuke.message(str(exc))
        return
    except Exception as exc:
        nuke.message(f"Capture export failed: {exc}")
        return

    nuke.message(f"Capture published to Kitsu and saved to:\n{output_path}")
