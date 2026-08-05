"""Nuke-side integration: everything that talks to Nuke itself.

This is the Nuke counterpart of what the Houdini version of this plugin
did through `hou`/`toolutils` (itself the counterpart of what the Maya
version did through `maya.cmds`) — kept in one module so the rest of the
code (panel UI, Kitsu API wrapper, task detection, drawover rendering)
stays host-agnostic:

- the current script's file path (for task detection + version parsing)
- a single-frame capture of what the Viewer is showing (what gets
  published as the preview, the equivalent of Maya's single-frame
  playblast / Houdini's single-frame flipbook)
- a full-range H.264 MP4 export of the same (Publish Capture) — unlike
  the Maya/Houdini ports this needs no external `ffmpeg` binary, since
  Nuke's own Write node encodes H.264 itself
- "Kitsu_Feedback_<revision>" nodes showing a review drawover on the
  Viewer's second input (the equivalent of Maya's "Feedback_<revision>"
  camera image plane / Houdini's viewport background image)

Both capture paths render the node the Viewer is currently displaying
through a temporary Write node, rather than grabbing the Viewer widget's
pixels: that renders the comp at full format resolution with Nuke's own
colour management, which is what a comp is normally reviewed as. Note
this is the image, not the Viewer's *display* state — the Viewer's
gain/gamma sliders and viewer process LUT are viewing transforms and are
deliberately not baked into the published preview.
"""

import os
import re

import nuke


class NukeSceneError(Exception):
    """A specific, user-facing reason a Nuke-side operation failed."""


# ---------------------------------------------------------------------------
# Script / timeline state
# ---------------------------------------------------------------------------


def scene_path():
    """Absolute path of the current script, or None if it was never saved.

    `nuke.root().name()` returns the literal string "Root" for an unsaved
    script (and `nuke.scriptName()` raises), so the `name` knob — empty
    until the first save — is what actually distinguishes the two.
    """
    path = nuke.root()["name"].value()
    return path or None


def scene_fps():
    """Frames per second of the current script."""
    return float(nuke.root()["fps"].value())


def playback_start():
    """First frame of the script's frame range — frame 0 of a published
    capture, since that's where a full-range export starts."""
    return int(nuke.root()["first_frame"].value())


def playback_range():
    """(first, last) frames of the script's frame range, inclusive —
    what a full-scene capture (see render_video) covers."""
    return (
        int(nuke.root()["first_frame"].value()),
        int(nuke.root()["last_frame"].value()),
    )


def current_frame():
    return int(nuke.frame())


def go_to_frame(frame):
    """Move the playhead — how frame-based review notes are navigated to
    in Nuke, which (unlike Maya, Houdini and Blender) has no scriptable
    timeline markers in its comp Viewer to place them on instead."""
    nuke.frame(int(frame))


def script_resolution():
    """The script's output format resolution (width, height)."""
    format_ = nuke.root().format()
    return int(format_.width()), int(format_.height())


def proxy_mode_enabled():
    """True if the script is in proxy mode, in which case anything
    rendered out of it — including this plugin's captures — comes out at
    the proxy resolution. Not changed behind the user's back; callers
    just say so when it's on."""
    return bool(nuke.root()["proxy"].value())


# ---------------------------------------------------------------------------
# The viewed node
# ---------------------------------------------------------------------------


def viewed_node():
    """The node the active Viewer is currently displaying.

    This is what "the viewport" means in Nuke for capture purposes: the
    input of the active Viewer that's switched on right now (the one the
    1/2/3... keys pick), not the Viewer node itself.
    """
    viewer = nuke.activeViewer()
    if viewer is None:
        raise NukeSceneError(
            "No Viewer is open — open one (and connect it to the node you "
            "want to publish) first."
        )

    node = viewer.node()
    if node is None:
        raise NukeSceneError("The active Viewer has no node to read from.")

    index = viewer.activeInput()
    if index is None or index < 0:
        raise NukeSceneError(
            "The active Viewer isn't showing anything — connect a node to "
            "it first."
        )

    source = node.input(index)
    if source is None:
        raise NukeSceneError(
            f"The active Viewer's input {index + 1} isn't connected to "
            "anything."
        )
    return source


# ---------------------------------------------------------------------------
# Capture (single frame + full range)
# ---------------------------------------------------------------------------


def _nuke_path(path):
    """Nuke wants forward slashes in file knobs on every platform."""
    return str(path).replace("\\", "/")


def _set_knob(node, name, value):
    """Set `name` on `node` if that knob exists on this Nuke version.

    Used for the codec/quality knobs of the MOV writer, whose exact names
    and accepted values have changed across Nuke versions (mov32_* ->
    mov64_*, and the profile knobs added later): a knob this build
    doesn't have, or won't take this value, should mean "this build
    doesn't offer that setting", not a failed export. Nuke 16 only logs
    a "Bad value" error for an unknown enum value rather than raising,
    but that isn't guaranteed of every version.
    """
    knob = node.knob(name)
    if knob is None:
        return False
    try:
        knob.setValue(value)
    except Exception:
        return False
    return True


def _execute(write_node, start_frame, end_frame):
    try:
        nuke.execute(write_node, int(start_frame), int(end_frame))
    except RuntimeError as exc:
        message = str(exc)
        if message.startswith("Cancelled"):
            raise NukeSceneError("The render was cancelled.") from exc
        raise NukeSceneError(f"Nuke could not render the capture: {message}") from exc


def _render_through_temp_write(source, target_path, start_frame, end_frame, configure):
    """Render `source` to `target_path` through a throwaway Write node.

    The Write node is created with undo disabled and deleted again in a
    `finally`, so a capture never shows up in the artist's undo stack and
    never survives in the script — not even if the render fails or is
    cancelled halfway.
    """
    if not nuke.canCreateNode("Write"):
        raise NukeSceneError(
            "This Nuke edition can't create Write nodes (Nuke Assist), so "
            "captures can't be rendered."
        )

    directory = os.path.dirname(target_path)
    if directory:
        os.makedirs(directory, exist_ok=True)

    nuke.Undo.disable()
    write = None
    try:
        write = nuke.nodes.Write(file=_nuke_path(target_path), channels="rgb")
        write.setInput(0, source)
        configure(write)
        _execute(write, start_frame, end_frame)
    finally:
        if write is not None:
            nuke.delete(write)
        nuke.Undo.enable()

    if not os.path.exists(target_path):
        raise NukeSceneError(
            f"Nuke reported no error but wrote no file to {target_path}."
        )
    return target_path


def capture_viewer(target_path, frame=None):
    """Render the currently viewed node at one frame to `target_path`.

    The single-frame equivalent of Maya's playblast / Houdini's flipbook:
    what the Viewer is showing, rendered at full format resolution.
    """
    source = viewed_node()
    frame = current_frame() if frame is None else int(frame)

    def configure(write):
        write["file_type"].setValue("png")
        _set_knob(write, "datatype", "8 bit")

    return _render_through_temp_write(source, target_path, frame, frame, configure)


def render_video(target_path, start_frame, end_frame, fps):
    """Render the currently viewed node over a frame range to an H.264 MP4.

    Uses Nuke's own MOV/ffmpeg writer (`mov64`) with the H.264 codec and
    an `.mp4` container, so — unlike the Maya and Houdini ports, which
    have to shell out to a system `ffmpeg` because their playblast/
    flipbook can't produce H.264 — nothing outside Nuke is needed.
    """
    source = viewed_node()

    def configure(write):
        # The file_type knob has to be set explicitly: it's the writer
        # that's chosen here ("mov" = Nuke's ffmpeg writer), while the
        # .mp4 extension only picks that writer's container.
        write["file_type"].setValue("mov")
        _set_knob(write, "mov64_codec", "h264")
        _set_knob(write, "mov64_fps", float(fps))
        _set_knob(write, "mov_h264_codec_profile", "High 4:2:0 8-bit")
        _set_knob(write, "mov64_quality", "High")
        # Puts the index at the head of the file so a player (or Kitsu's
        # own web player) can start streaming before the whole download
        # finishes — the same thing ffmpeg's "-movflags +faststart" does
        # in the Maya/Houdini ports.
        _set_knob(write, "mov64_fast_start", True)

    return _render_through_temp_write(
        source, target_path, start_frame, end_frame, configure
    )


# ---------------------------------------------------------------------------
# Review feedback in the Viewer
# ---------------------------------------------------------------------------

_FEEDBACK_PREFIX = "Kitsu_Feedback_"
_FEEDBACK_TILE_COLOR = 0x44B58CFF  # teal-green, distinct from Nuke's defaults
_FEEDBACK_VIEWER_INPUT = 1  # the Viewer's second input, i.e. the "2" key


def _feedback_names(revision):
    """Node names for one revision's feedback: the node that gets viewed,
    plus the helper nodes behind it for the video-drawover case."""
    # Node names are identifiers in Nuke — a revision is normally an int,
    # but it's rendered as "?" when Kitsu didn't give one.
    suffix = re.sub(r"\W", "_", str(revision))
    base = f"{_FEEDBACK_PREFIX}{suffix}"
    return base, f"{base}_Drawover", f"{base}_Premult"


def _delete_existing(names):
    """Replace, rather than stack, this revision's previous feedback nodes
    — same contract as the Maya port's named image plane."""
    for name in names:
        node = nuke.toNode(name)
        if node is not None:
            nuke.delete(node)


def _place_near(node, reference, offset_x=180, offset_y=80):
    if reference is None:
        return
    node.setXYpos(reference.xpos() + offset_x, reference.ypos() + offset_y)


def _show_in_viewer(node):
    """Wire `node` to the Viewer's second input and switch to it, so the
    artist can flip between their comp (1) and the feedback (2).

    Best-effort: `nuke.connectViewer` is one of the calls Nuke refuses
    outright when there's no UI (a terminal/batch session), and the node
    itself — the part worth keeping — has already been created by the
    time this runs. So a failure here is reported to the Script Editor
    and left at that, rather than failing the whole operation for
    something the artist can also just do by hand.
    """
    try:
        nuke.connectViewer(_FEEDBACK_VIEWER_INPUT, node)
        viewer = nuke.activeViewer()
        if viewer is not None:
            viewer.activateInput(_FEEDBACK_VIEWER_INPUT)
    except RuntimeError as exc:
        nuke.tprint(
            f"Kitsu: created '{node.name()}' but could not connect it to the "
            f"Viewer ({exc}) — connect it by hand to see it."
        )
        return False
    return True


def set_feedback_image(image_path, revision):
    """Show a still revision (with its drawover composited on) in the Viewer.

    Creates a Read node named `Kitsu_Feedback_<revision>` and puts it on
    the Viewer's second input: pressing 2 shows the reviewer's image,
    pressing 1 goes back to the comp. Delete the node when done with it.
    """
    base_name, drawover_name, premult_name = _feedback_names(revision)

    nuke.Undo.disable()
    try:
        _delete_existing((base_name, drawover_name, premult_name))
        read = nuke.nodes.Read(file=_nuke_path(image_path), name=base_name)
        read["tile_color"].setValue(_FEEDBACK_TILE_COLOR)
        read["label"].setValue(f"Kitsu revision {revision}")
        try:
            _place_near(read, viewed_node())
        except NukeSceneError:
            pass  # no Viewer to place it relative to; leave it where it landed
        _show_in_viewer(read)
    finally:
        nuke.Undo.enable()

    return base_name


def set_feedback_drawover_sequence(sequence_pattern, first_frame, last_frame, revision):
    """Show a per-frame drawover sequence over the comp in the Viewer.

    `sequence_pattern` is a printf-style path (e.g. ".../drawover.%04d.png")
    whose files are numbered by absolute Nuke frame — each annotated frame
    holds that frame's markup on a transparent background (the caller
    writes them, see panel.py). Frames outside [first_frame, last_frame]
    read as transparent black rather than erroring, so scrubbing past the
    annotated part of the timeline simply shows nothing.

    The sequence is merged over whatever the Viewer is currently showing
    into a node named `Kitsu_Feedback_<revision>`, which is then put on
    the Viewer's second input: the artist's own node graph is left
    untouched (nothing is rewired), and deleting the three
    `Kitsu_Feedback_<revision>*` nodes removes the overlay again.
    """
    base_name, drawover_name, premult_name = _feedback_names(revision)
    base = viewed_node()  # resolved before anything is created, so a
                          # missing Viewer fails before touching the script

    nuke.Undo.disable()
    try:
        _delete_existing((base_name, drawover_name, premult_name))

        read = nuke.nodes.Read(
            file=_nuke_path(sequence_pattern),
            first=int(first_frame),
            last=int(last_frame),
            on_error="black",
            name=drawover_name,
        )
        read["tile_color"].setValue(_FEEDBACK_TILE_COLOR)
        read["label"].setValue(f"Kitsu revision {revision} drawovers")

        # PNG stores straight (un-premultiplied) alpha, which is what
        # QPainter wrote out in panel.py, but Nuke's "over" expects
        # premultiplied input — without this the antialiased edges of the
        # reviewer's strokes come out too bright over the comp.
        premult = nuke.nodes.Premult(inputs=[read], name=premult_name)

        merge = nuke.nodes.Merge2(inputs=[base, premult], name=base_name)
        merge["tile_color"].setValue(_FEEDBACK_TILE_COLOR)
        merge["label"].setValue(f"Kitsu revision {revision}")

        _place_near(read, base, offset_y=120)
        _place_near(premult, read, offset_x=0, offset_y=60)
        _place_near(merge, base, offset_y=220)

        _show_in_viewer(merge)
    finally:
        nuke.Undo.enable()

    return base_name
