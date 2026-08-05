# Kitsu Nuke Plugin

A Nuke plugin that connects to a self-hosted Kitsu/Zou (CG Wire)
instance: it detects the task a script belongs to from its folder
structure, shows feedback/comments (including drawover attachments), and
publishes new versions with a comment and status change.

This is the Nuke counterpart of a family of ports of the same plugin for
Houdini, Maya, Krita and Blender — same features, same UI
layout, same Kitsu-side behavior, with the host-specific pieces swapped
for their Nuke equivalents (a Write-node render of what the Viewer shows
instead of a flipbook, feedback nodes on the Viewer's second input
instead of a viewport background image).

All Kitsu/Zou protocol handling (auth, endpoints, uploads/downloads) is
delegated to CGWire's official [`gazu`](https://github.com/cgwire/gazu)
Python client. Nuke's bundled Python doesn't have `gazu` or `requests`,
so both are vendored inside
`kitsu_nuke_plugin/python/kitsu_nuke_plugin/vendor/` along with
`requests`'s own dependencies (`urllib3`, `certifi`, `idna`,
`charset_normalizer`). No manual `pip install` into Nuke's Python is
required.

Built and verified against **Nuke 16.0v6** (Python 3.11, PySide6/Qt
6.5). The Qt imports fall back to PySide2, so it should also run on Nuke
13–15, but only Nuke 16 was actually tested — see "Verification status"
below for exactly what was and wasn't exercised.

## Differences from the Maya/Houdini/Krita/Blender versions

Every feature from the other four ports is present here — nothing is
dropped — but a few are implemented differently because Nuke's own
capabilities are different:

- **"Capture" means a render, not a screen grab.** Maya playblasts the
  viewport and Houdini flipbooks it; Nuke instead renders the node the
  Viewer is currently showing (the input the 1/2/3… keys pick) through a
  temporary Write node, at full format resolution with Nuke's own colour
  management. The Write node is created with undo disabled and deleted
  again in a `finally`, so a capture never lands in the undo stack or
  survives in the script. Note this publishes the *image*, not the
  Viewer's display state: the Viewer's gain/gamma sliders and viewer
  process LUT are viewing transforms and are deliberately not baked in.
  If the script is in **proxy mode**, everything Nuke renders — captures
  included — comes out at proxy resolution; the panel says so rather
  than changing that setting behind your back.
- **Full-scene video export** ("Publish Capture") needs no external
  `ffmpeg` binary at all: Nuke's own Write node encodes H.264 into an
  `.mp4` directly (the Maya and Houdini ports have to shell out to a
  system `ffmpeg`, because neither playblast nor flipbook can produce
  H.264). Only Blender's port is similarly self-contained.
- **Drawovers become nodes on the Viewer's second input.** Maya attaches
  a camera image plane and Houdini sets a viewport background image;
  Nuke gets real nodes named `Kitsu_Feedback_<revision>`, wired to the
  Viewer's input 2 and switched to, so **2** shows the reviewer's markup
  and **1** goes back to your comp. Your own node graph is never
  rewired — the feedback nodes are added alongside it, and deleting them
  removes the overlay again. Re-clicking for the same revision replaces
  that revision's nodes instead of stacking duplicates.
- **There is no "Add Timeline Markers".** Nuke's comp Viewer has no
  scriptable timeline markers to place them on — its timeline carries
  only the playhead and in/out points, and the frame markers people
  remember are a Nuke Studio editorial-timeline feature, not a comp one.
  Instead of marking annotated frames in place, the panel lists them in
  a **picker with a "Go to Frame" button** that jumps the playhead
  straight to the frame a note was drawn on. (The per-frame drawover
  overlay itself is unaffected and works exactly like the other ports'.)
- **No shelf button.** Maya has "Add Shelf Button" and Houdini ships a
  shelf; Nuke's equivalent surfaces are the **menu bar** ("Kitsu")
  and the **pane menu** (the panel is registered as "Kitsu", so it can
  be added to any pane like the Properties or Curve Editor panels).
  Both are set up by the plugin's own `menu.py`.

## Folder layout

Everything under `kitsu_nuke_plugin/` is exactly what gets copied into
`~/.nuke`:

```
kitsu_nuke_plugin/
  init.py                      # Nuke startup (GUI + terminal): puts python/ on sys.path
  menu.py                      # Nuke GUI startup: "Kitsu" menu + panel registration
  icons/
    kitsu_nuke_plugin.png      # menu icon: the Kitsu fox logo
  python/
    kitsu_nuke_plugin/         # the plugin package
      __init__.py
      qt.py                    # PySide6/PySide2 binding shim
      panel.py                 # the panel UI (login, task, feedback, publish)
      menu_actions.py          # what the menu entries do (open panel, publish capture)
      collapsible_section.py   # collapsible header used for each panel section
      kitsu_api.py             # wraps vendored gazu for login/tasks/comments
      task_detection.py        # resolves asset/shot task from folder structure
      nuke_scene.py            # script path, Viewer capture, video export, feedback nodes
      video_annotations.py     # per-frame drawover extraction for video previews
      publish_capture.py       # "Kitsu > Publish Capture": full-range MP4 + Kitsu upload
      capture_dialog.py        # status/comment dialog shown before a Publish Capture export
      capture_naming.py        # studio review-file naming convention for Publish Capture
      settings.py              # persists server URL / email / project id / collapsed sections
      versioning.py            # parses "_v###" filename versions
      annotations.py           # renders Kitsu drawovers (Fabric.js shapes) locally
      vendor/
        gazu/                  # vendored CGWire gazu client
        requests/, urllib3/,   # vendored gazu runtime dependencies
        certifi/, idna/, charset_normalizer/
        typing_extensions.py   # shim (Nuke's Python already has typing.Literal)
```

The package deliberately sits in a `python/` subfolder rather than next
to `init.py`. Nuke puts **every** plugin-path folder on `sys.path`, so
anything beside `init.py` would become importable under its own bare
name — a `panel.py` or `settings.py` at that level could shadow another
tool's module of the same name. Only `python/` (which contains nothing
but the package) is added to `sys.path`, so this plugin's modules are
reachable exclusively as `kitsu_nuke_plugin.*`.

## Installation

### Automatically

Run the installer script for your OS from the repository root — each
copies `kitsu_nuke_plugin/` into your `~/.nuke` folder (removing any
previous install of the plugin's own folder first, so nothing stale from
an older version is left behind) and appends two lines to
`~/.nuke/init.py` that tell Nuke to load it:

- **Windows**: double-click `install_windows.cmd` (installs to
  `%USERPROFILE%\.nuke`).
- **macOS**: double-click `install_mac.command` (installs to `~/.nuke`).
  If it won't open ("not executable"), run `chmod +x
  install_mac.command` once in Terminal first.
- **Linux**: run `./install_linux.sh` in a terminal (`chmod +x
  install_linux.sh` first if needed). Installs to `~/.nuke`.

`~/.nuke` is version-independent — every installed Nuke version scans it
at startup, so one install covers all of them. If you keep your Nuke
setup somewhere else (a folder on `NUKE_PATH`), pass that folder as an
argument to the script instead, e.g. `./install_linux.sh
/studio/nuke_config`.

Re-running an installer is safe: the plugin folder is replaced, and the
`init.py` entry is only added if it isn't already there — your own
`init.py` content is never rewritten, only appended to.

### Manually

1. Copy the `kitsu_nuke_plugin/` folder into your `.nuke` folder
   (create it if it doesn't exist):
   - Windows: `%USERPROFILE%\.nuke`
   - macOS / Linux: `~/.nuke`
2. Add this to `~/.nuke/init.py` (create the file if it doesn't exist):
   ```python
   import nuke
   nuke.pluginAddPath("./kitsu_nuke_plugin")
   ```
   This line is what actually activates the plugin. Nuke only auto-runs
   `init.py`/`menu.py` for folders that are **on** its plugin path, and
   it never looks inside sub-folders on its own — so without it the
   files are installed but nothing loads them.
3. Restart Nuke. A **"Kitsu"** menu appears in the menu bar with
   **Open Kitsu Panel** and **Publish Capture**. The panel is also
   listed as **"Kitsu"** in the pane menu (the ☰ button of any pane, or
   the "+" tab menu), so it can be docked, tabbed or floated like any
   other Nuke panel.

### Shared / studio-wide deployment

To deploy the plugin for a whole project or a whole studio instead of
per-user, put the `kitsu_nuke_plugin/` folder inside any location that is
already on `NUKE_PATH` — a shared Nuke workgroup folder, or a project's
own Nuke plugin folder, e.g.:

```
<SHARED_NUKE_FOLDER>/kitsu_nuke_plugin
```

Then add this one line to the **parent** folder's `init.py` (creating that
file if it doesn't have one):

```python
import nuke
nuke.pluginAddPath("./kitsu_nuke_plugin")
```

That line is what actually activates the plugin. Nuke scans plugin-path
folders for `init.py`/`menu.py` but never descends into sub-folders on its
own, so without it the files are deployed but nothing loads them.

If you script this rollout, mirror `kitsu_nuke_plugin/` into the target
and only ever *append* the `pluginAddPath` line — check for it first so
re-running the rollout doesn't duplicate the entry, and never overwrite
existing `init.py` content, since that file usually belongs to the studio
rather than to this plugin. Point the mirror at the plugin's own
`kitsu_nuke_plugin` folder, never at the shared plugin folder that
contains it.

Use either the per-user install **or** a shared deployment, not both: two
copies on `NUKE_PATH` would build the "Kitsu" menu twice.

### If the plugin doesn't show up

Open the Script Editor — any error from `init.py`/`menu.py` at startup
prints there. Since `gazu` and `requests` (plus their dependencies) are
fully vendored, and every menu command imports lazily (the menu is built
from command strings, and the panel widget is only constructed when the
panel is actually opened), a problem in the vendored libraries can only
fail the specific command that hit it — never Nuke's startup.

If you get an error like `module 'gazu.xyz' has no attribute '...'` for
something this plugin clearly uses, it means some *other* `gazu` package
is being found before this plugin's own vendored copy — e.g. a leftover
`pip install gazu`, or a studio-wide `PYTHONPATH` entry pointing at a
different version. The vendored copy is always inserted first on
`sys.path`, and every Login attempt also clears out any *already
imported* `gazu` that didn't come from this plugin's own `vendor/`
folder — so this should self-heal on your very next Login without
restarting Nuke. If it still doesn't, run
`import gazu; print(gazu.__file__)` in the Script Editor: if the path
shown isn't inside this plugin's own `vendor/gazu/`, that confirms
something is re-importing its own `gazu` even more aggressively and
points at what to remove from your Python environment.

## Using the plugin

Each section (Connection, Task, Feedback, Publish) has a clickable title
that collapses/expands it — handy for reclaiming vertical space once you
don't need, say, the Connection or Task section visible anymore.
Collapsed/expanded state is remembered per section across Nuke restarts.

Every network call the panel makes on a timer or on a click that could
be slow (login, task detection, the background comment refresh) runs on
a **background thread**, so a slow or unreachable Kitsu server never
freezes Nuke's UI; every request also has a 10-second timeout.

1. Open the Kitsu panel and enter your server URL (e.g.
   `https://kitsu.yourstudio.com`), email + password (or an API token),
   and the project ID, then click **Login**.
   - The server URL is normalized to end in `/api` automatically (gazu's
     convention), matching how the official CGWire `gazu` client expects
     the host to be configured.
   - If login fails, the panel shows the *specific* reason (rejected
     credentials, a 404 route, a server error, etc.) instead of a generic
     failure — if you get a 404, it usually means the Zou API for this
     Kitsu instance lives at a different host/path than the web UI, and
     you'll need to ask whoever administers the server for the correct
     API URL.
   - Once logged in, a **"Welcome, `<your name>`"** greeting and your
     Kitsu avatar appear at the bottom of the Connection section,
     confirming at a glance which account you're connected as. Accounts
     without an avatar set on Kitsu just show the greeting.
   - Logging in with email/password automatically fills in and saves the
     **API token** field with a fresh refresh token. From then on, **every
     time you open the panel with a server URL, project ID, and that
     token already filled in, it logs in automatically** — no click
     needed. This token isn't your password (which is never saved — see
     Notes on security) and it eventually expires on its own; if it has,
     the automatic attempt just fails quietly (shown in the status line,
     not a popup) and you log in with your password once more, which
     replaces it with a fresh one.
   - Once logged in, the project's **thumbnail and name** show at the top
     of the **Task** section, above the detected asset/shot breadcrumb.
     Editing the Project ID field afterwards clears both until you log in
     again, so they never show stale info for a different project.
2. Open a script and click **Detect Task** — the plugin resolves the
   Kitsu task from the script's folder structure (folder names matched
   case-insensitively against Kitsu's names). Both **asset** and **shot**
   contexts are supported:

   | Context | Expected folder layout above the file |
   | --- | --- |
   | Asset | `.../<AssetType>/<AssetName>/<TaskType>/file.nk`<br>e.g. `assets/characters/Hero/lookdev/Hero_lookdev_v002.nk` |
   | Shot (movie / short / commercial) | `.../<Sequence>/<Shot>/<TaskType>/file.nk`<br>e.g. `shots/seq010/sh0100/compositing/sh0100_comp_v003.nk` |
   | Shot (TV series, with episodes) | `.../<Episode>/<Sequence>/<Shot>/<TaskType>/file.nk`<br>e.g. `episodes/ep01/seq010/sh0100/compositing/sh0100_comp_v003.nk` |

   The plugin decides **asset vs. shot** from an anchor folder anywhere in
   the path (case-insensitive): a folder named `assets`/`asset` means
   asset context, while `shots`/`shot`/`sequences`/`sequence`/`episodes`/
   `episode` means shot context. With no such anchor it assumes an asset.
   It decides whether shots sit **under episodes** from the *project
   itself* — only a Kitsu `tvshow` production has episodes.

   If the task-type folder name doesn't match any task type in the
   project, the panel offers a **task-type picker** instead of just
   failing; the choice is remembered for that exact file path, so the
   next Detect Task on the same script resolves silently.

   The detected breadcrumb is shown in the Task section along with the
   task's current **Status**, **Due Date** ("Not set" if Kitsu has none),
   and a **timesheet** for logging hours worked on this task today: a
   slider (0–12h, in half-hour steps), **1h / 4h / 8h** preset buttons,
   and a **Log Time** button that submits it — matching Kitsu's own web
   timesheet slider. Submitting **sets** the day's total rather than
   adding to it, and detecting a task you've already logged time on today
   starts the slider at that value.

   The slider also **auto-advances**: from the moment a task is detected
   it counts up in real time from whatever's already logged today, so
   after an hour of work it reads "1h" without you touching anything.
   Dragging it (or clicking a preset) pauses the auto-advance so it never
   fights a value you set on purpose; the value label shows "(auto)"
   while it's still counting. Clicking **Detect Task** again for the
   *same* task leaves the tracker exactly as it was — only a genuine
   change of task or a successful **Log Time** restarts it.
3. Existing comments for that task show up in the **Feedback** section,
   each listed as `<STATUS> - <name>: <comment text>`, prefixed with
   `Revision <n>` when the comment introduced a new published revision.

   The list also **auto-refreshes in the background** every 60 seconds
   while a task is detected — but only when something actually changed,
   and a comment you have selected stays selected. A background check
   that fails is silent and just retries on the next tick. Select a
   comment to see, below the list:
   - Its **checklist**, if it has one, as tickable checkboxes — ticking
     one syncs back to Kitsu immediately (and reverts with a warning if
     the sync fails, so the UI never shows a state that isn't saved).
   - Its **revisions**, embedded inline, with any Kitsu **drawover**
     composited directly on top of the image, labeled "(with drawover)".
     If a revision has a drawover, click **Show in Viewer** to read it
     into the script as a node named `Kitsu_Feedback_<revision>`, wired
     to the Viewer's second input: press **2** to see the reviewer's
     image, **1** to go back to your comp. Clicking again for the same
     revision replaces that node rather than stacking duplicates; delete
     it when you're done with it.
   - Its **attachments** (other reference images), embedded inline. Click
     **Save Attachment(s)** if you want a local copy.

### Frame-based feedback on video revisions

When a revision is a **video** (e.g. a published playblast or comp
render), reviewers in Kitsu draw their notes on specific frames, and the
panel shows the revision as its thumbnail with the list of annotated
frames plus:

- A **frame picker + "Go to Frame"**, which moves the playhead to the
  frame a note was drawn on. (This is where the other ports put "Add
  Timeline Markers" — see "Differences" above for why Nuke gets
  navigation instead of markers.)
- **Show Drawovers in Viewer**, which builds a `Kitsu_Feedback_<revision>`
  node showing each frame's drawover **only on that exact frame**: the
  markup is rendered onto transparent images (one per frame of the
  annotated range), read back as an image sequence, and merged over
  whatever the Viewer is currently showing. Stepping to a marked frame
  shows the reviewer's strokes over your live comp; scrubbing away hides
  them. It lands on the Viewer's second input (**2** to see it, **1** for
  your comp), leaves your own graph unrewired, and re-clicking replaces
  it. Three nodes are created — `Kitsu_Feedback_<revision>` (the merge)
  plus its `_Drawover` (the Read) and `_Premult` inputs — delete them
  when done.

Frame mapping: Kitsu counts video frames from 0, and frame 0 of a
published capture is the first frame of your script's frame range — so
notes land at `first frame + Kitsu frame`. If you publish captures of a
different range than you work in, set the frame range to the published
one before navigating. The frame⇄time conversion uses the Kitsu
production's fps, falling back to the script's fps if the production
doesn't define one.

4. To publish, pick a status, write a comment, queue the image(s) you
   want to show, and click **Publish**.

   **Nothing is captured automatically.** Queue images explicitly with
   **+ From Viewer** (renders what the Viewer is showing at the current
   frame) or **+ From File...** (browse for an existing image, e.g. a
   frame from a render), listed above the Publish button, with **Remove
   Selected** to drop one. The first image becomes the revision's main
   preview; the rest are uploaded as additional preview files on the
   **same revision/comment** (Kitsu's own multi-preview-per-revision
   support), so they show up as flippable variations of that one version
   rather than separate revisions or plain attachments. If the list is
   empty, Publish just posts the status change and comment with no
   preview — a status change like "starting work" never silently
   publishes a picture of your comp.

   Published previews are proper Kitsu **revisions** (not plain comment
   attachments), so they appear in the task's version history and can be
   drawn over in review sessions. If the script filename ends in a
   `_v###`-style version (e.g. `sh0100_comp_v003.nk`), that number is
   used as the revision number on Kitsu too.

   The queue is cleared as each image uploads successfully; if the main
   publish fails, none are touched, and if a particular variation's
   upload fails, only that one stays queued (with a clear warning) so
   it's easy to retry without re-adding it.

### Publish Capture: full-range video export

The Publish button above exports a single frame. For a full-range H.264
MP4 of your script's frame range, published to Kitsu as a new revision,
use **Kitsu → Publish Capture** in the menu bar.

1. **Requirements**: the panel must already be open, logged in, and have
   a task detected (Publish Capture reuses that state rather than asking
   you to log in again), the script must be saved, and the Viewer must be
   showing something. **No `ffmpeg` install is needed** — unlike the Maya
   and Houdini ports, Nuke encodes the H.264 itself.
2. A small dialog asks for a **task status** and a **comment**, the same
   two fields the panel's own Publish section asks for.
3. The script's full frame range is rendered at its own fps, encoded to
   H.264, saved locally, and **published to Kitsu as a new revision** on
   the detected task. If the upload itself fails (e.g. a dropped
   connection), the video stays on disk and the error message says
   exactly where, so nothing is lost.

**Output**: saved as `<script folder>/capture/<name>.mp4`. The file name
follows:

```
<Show>[_<Episode>]_<Sequence>_<Shot>_v<version>_<Initial><Lastname>.mp4
```

e.g. `MyShow_seq010_sh0100_v003_JDoe.mp4`, or with an episode for a TV
show, `MyShow_ep01_seq010_sh0100_v003_JDoe.mp4`. For an asset script the
analogous fallback substitutes the asset type and asset name, e.g.
`MyShow_characters_Hero_v003_JDoe.mp4`. The version number comes from the
script's own `_v###` filename (omitted if there isn't one, and also used
as the Kitsu revision number); the trailing name is the logged-in Kitsu
user's first initial + last name.

Naming conventions are one of the most studio-specific parts of a
pipeline, so this is kept in its own small function — swap
`capture_naming.py`'s `build_capture_filename` if yours differs, without
touching the render/encode/upload logic in `publish_capture.py`.

### Drawover rendering limitations

Drawover markup is Kitsu's own Fabric.js canvas data (rectangles,
circles, arrows, freehand strokes, text notes), re-drawn locally in
[annotations.py](kitsu_nuke_plugin/python/kitsu_nuke_plugin/annotations.py)
with `QPainter` — this covers everything Kitsu's own drawover toolbar
produces. Not (yet) supported: the eraser tool's mask, nested groups,
and rotation on freehand strokes/lines/arrows specifically (rotation on
rectangles/circles/text works). A shape that can't be drawn is skipped
rather than breaking the rest of the drawover.

## Verification status

Built and tested against the locally installed **Nuke 16.0v6** (Python
3.11.7, PySide6 6.5.3). Nuke's GUI could not be launched from the
development environment at all — a plain `Nuke16.0.exe` with no plugin
and no script aborts there during startup with an internal ZeroMQ error
— so everything below was exercised in Nuke's terminal mode (`-t`), which
runs the real `nuke` module against the real installed build:

- **Verified in Nuke**: every module imports; the installer's
  `init.py` entry loads the plugin and makes the package importable
  (including re-running the installer without duplicating the entry);
  task detection, `_v###` version parsing, review-file naming,
  annotated-frame extraction and the time-spent coercion helper all
  produce the expected values; `scene_path`/`fps`/frame range/format/
  proxy/current-frame all read correctly off `nuke.root()`; a
  single-frame **PNG render** and a full-range **H.264 MP4** (verified as
  a real `ftypisom` MP4) both render through the temporary Write node,
  which is cleaned up afterwards in both cases; the
  `Kitsu_Feedback_<revision>` nodes are created, named, wired
  (Read → Premult → Merge over the viewed node) and replaced-not-stacked
  on a second click; "no Viewer open" and "not logged in / no task"
  paths raise their specific user-facing messages.
- **Not testable in terminal mode** (Nuke refuses these without a UI,
  which is not a bug — the plugin only ever runs in the GUI): building
  the "Kitsu" menu and registering the panel (`nuke.menu('Pane')`
  raises "not in GUI mode"), constructing the panel widget, and the
  `nuke.connectViewer` call that puts a feedback node on the Viewer's
  second input. That last one is best-effort by design: if it fails, the
  node has still been created and the reason is printed to the Script
  Editor rather than failing the whole operation.
- **Not exercised at all**: anything requiring a live Kitsu server —
  login, task/comment fetching, uploads, timesheet writes. The Kitsu-side
  code is shared with the Maya/Houdini/Krita/Blender ports and unchanged
  apart from the per-person time-spent lookup, which is carried over from
  the Blender port's corrected version.

Recommended before production use: open a real Nuke 16 session and walk
through Login → Detect Task → Feedback (including a comment with a
drawover) → Publish → Publish Capture once, against a real (or
disposable test) Kitsu project.

## Notes on security

The account password is never written to disk — only the server URL,
email, project ID, and API token are persisted (via `QSettings`) across
Nuke restarts.

The API token field holds a **refresh token**, not your password: after
logging in with email/password, this plugin saves the refresh token
Kitsu's own auth system issued for that login, so future logins can use
it instead of typing the password again. Unlike a password, it's
revocable and time-limited; if it ever expires or is revoked, logging in
with email/password once more simply gets and saves a fresh one. It's
stored in plain text the same way the other non-secret fields are, so
treat it with the same care you'd give any bearer credential — anyone
with it can act as your account until it expires.

## License

This plugin is licensed under the **GNU Lesser General Public License,
version 3** — the full text is in [LICENSE](LICENSE). LGPL-3.0 incorporates
the terms of GPL-3.0 by reference, so a copy of that text is included as
[COPYING.GPL-3.0](COPYING.GPL-3.0) as well.

LGPL rather than GPL is deliberate: it is the license that explicitly
permits combining with proprietary code, which is what a plugin importing
Nuke's closed-source `nuke` module does. Using it inside your studio is
unrestricted; if you distribute a *modified* version of the plugin, your
changes to it are expected to be available under the LGPL too.

> **TODO before publishing:** add the copyright line for the rights holder,
> e.g. `Copyright (C) 2026 <holder>`, here and — if you want the standard
> FSF layout — as a short header in each source file. The `LICENSE` text
> itself is the verbatim FSF document and correctly carries no project
> name; the copyright notice is a separate statement.

## Third-party components

The vendored libraries under
`kitsu_nuke_plugin/python/kitsu_nuke_plugin/vendor/` are third-party code,
redistributed unmodified under their own licenses, each of which is
included next to the library it applies to:

| Vendored library | License | License file |
| --- | --- | --- |
| [`gazu`](https://github.com/cgwire/gazu) 1.2.0 (CGWire) | LGPL-3.0 | `vendor/gazu-LICENSE` |
| [`requests`](https://github.com/psf/requests) | Apache-2.0 | `vendor/requests-LICENSE` |
| [`urllib3`](https://github.com/urllib3/urllib3) | MIT | `vendor/urllib3-LICENSE` |
| [`certifi`](https://github.com/certifi/python-certifi) | MPL-2.0 | `vendor/certifi-LICENSE` |
| [`idna`](https://github.com/kjd/idna) | BSD-3-Clause | `vendor/idna-LICENSE` |
| [`charset_normalizer`](https://github.com/jawah/charset_normalizer) | MIT | `vendor/charset_normalizer-LICENSE` |

`gazu` is **LGPL-3.0**, the same license as this plugin, so the two sit
together without any special handling. It is still vendored as a separate,
unmodified copy in source form, which keeps it replaceable: swapping
`vendor/gazu/` for another build of the same library is all that's needed,
and no other vendored file imports it. `vendor/typing_extensions.py` is
not third-party code but a nine-line shim written for this plugin, which
re-exports `typing.Literal` for `gazu`'s benefit.

The menu/panel icon `kitsu_nuke_plugin/icons/kitsu_nuke_plugin.png` is the
Kitsu logo, which belongs to CGWire and is used here only to identify the
Kitsu integration. Replace it if you redistribute a modified fork.
