import sublime
import sublime_plugin

MODE_INSERT = "insert"
MODE_NAVIGATE = "navigate"

# String mode (status / commands) + boolean for keymap context (setting.* is
# reliable with true/false; string match was flaky for bare letter keys).
SETTING = "fourcoder_modal_mode"
NAVIGATE_FLAG = "fourcoder_navigate"
STATUS_KEY = "fourcoder_modal"

# Commands that must run on the window, not the view.
WINDOW_COMMANDS = {
    "new_file",
    "prompt_open_file",
    "show_overlay",
    "show_panel",
    "focus_neighboring_group",
    "goto_symbol_in_project",
    "goto_definition",
    "next_result",
    "prev_result",
    "jump_back",
    "build",
    "close",
    "prev_view",
    "next_view",
    "set_layout",
    "save",
    "lsp_symbol_definition",
    "lsp_symbol_references",
    "lsp_symbol_rename",
    "terminus_open",
}

# Bare key (+ optional shift) -> (command, args). Mirrors Default.sublime-keymap ctrl chords.
BINDINGS = {
    ("space", False): ("set_mark", {}),
    ("space", True): ("select_to_mark", {}),
    ("=", False): ("set_mark", {"swap": True}),
    ("a", False): ("select_all", {}),
    ("c", False): ("_fourcoder_copy", {}),
    ("c", True): ("copy", {}),
    ("x", False): ("_fourcoder_cut", {}),
    ("x", True): ("cut", {}),
    ("v", False): ("paste", {}),
    ("z", False): ("undo", {}),
    ("y", False): ("redo", {}),
    ("d", False): ("new_file", {}),
    ("o", False): ("prompt_open_file", {}),
    ("p", False): ("show_overlay", {"overlay": "goto", "text": ""}),
    ("s", False): ("save", {}),
    ("t", False): ("focus_neighboring_group", {}),
    ("f", False): ("show_panel", {"panel": "find"}),
    ("f", True): (
        "run_macro_file",
        {"file": "res://Packages/User/find_in_selection.sublime-macro"},
    ),
    ("h", False): ("show_panel", {"panel": "replace"}),
    ("h", True): (
        "run_macro_file",
        {"file": "res://Packages/User/replace_in_selection.sublime-macro"},
    ),
    ("g", False): ("show_overlay", {"overlay": "goto", "text": ":"}),
    ("y", True): ("show_panel", {"panel": "find_in_files"}),
    ("j", False): ("join_lines", {}),
    ("j", True): ("duplicate_line", {}),
    ("k", False): (
        "run_macro_file",
        {"file": "res://Packages/Default/Delete Line.sublime-macro"},
    ),
    ("l", False): (
        "run_macro_file",
        {"file": "res://Packages/User/copy_line.sublime-macro"},
    ),
    ("l", True): (
        "run_macro_file",
        {"file": "res://Packages/User/cut_line.sublime-macro"},
    ),
    ("n", False): ("move_to", {"to": "bol", "extend": False}),
    ("m", False): ("move_to", {"to": "eol", "extend": False}),
    ("i", False): ("show_overlay", {"overlay": "goto", "text": "@"}),
    ("i", True): ("goto_symbol_in_project", {}),
    ("q", False): ("goto_definition", {}),
    ("q", True): ("lsp_symbol_definition", {"split_view": True}),
    ("w", False): ("next_result", {}),
    ("e", False): ("prev_result", {}),
    ("u", False): ("lsp_symbol_references", {}),
    ("r", False): ("lsp_symbol_rename", {}),
    ("5", False): ("find_under_expand", {}),
    ("5", True): ("find_under_expand_skip", {}),

    ("6", False): ("find_next", {}),
    ("7", False): ("find_prev", {}),
    ("9", False): ("move", {"by": "subword_ends", "forward": False}),
    ("0", False): ("move", {"by": "subword_ends", "forward": True}),
    ("-", False): ("expand_selection", {"to": "brackets"}),
    ("/", False): ("toggle_comment", {"block": False}),
    ("/", True): ("toggle_comment", {"block": True}),
    ("[", False): ("move_to_blank_line", {"forward": False}),
    ("]", False): ("move_to_blank_line", {"forward": True}),
    ("[", True): ("swap_line_up", {}),
    ("]", True): ("swap_line_down", {}),
    ("\\", False): (
        "build",
        {"build_system": "Packages/User/win32_msvc.sublime-build"},
    ),
    ("\\", True): ("show_panel", {"panel": "output.exec", "toggle": True}),
    ("`", False): ("jump_back", {}),
    ("d", True): ("close", {}),
    ("n", True): ("prev_view", {}),
    ("m", True): ("next_view", {}),
    ("1", True): (
        "set_layout",
        {
            "cols": [0.0, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1]],
        },
    ),
    ("2", True): (
        "set_layout",
        {
            "cols": [0.0, 0.5, 1.0],
            "rows": [0.0, 1.0],
            "cells": [[0, 0, 1, 1], [1, 0, 2, 1]],
        },
    ),
}

TEXT_KEYS = (
    list("abcdefghijklmnopqrstuvwxyz")
    + list("0123456789")
    + ["space", "-", "=", "[", "]", "\\", "/", "`", ";", "'", ",", "."]
)


def default_mode():
    return sublime.load_settings("Preferences.sublime-settings").get(
        "fourcoder_modal_default_mode", MODE_INSERT
    )


def mode_label(mode):
    return "-- NAVIGATE --" if mode == MODE_NAVIGATE else "-- EDIT --"


def apply_mode_visuals(view):
    mode = view.settings().get(SETTING, default_mode())
    navigate = mode == MODE_NAVIGATE
    view.settings().set(NAVIGATE_FLAG, navigate)
    view.settings().set("block_caret", navigate)
    view.settings().set("caret_extra_width", 1 if navigate else 2)
    view.set_status(STATUS_KEY, mode_label(mode))


def ensure_mode(view):
    if view.settings().get(SETTING) is None:
        view.settings().set(SETTING, default_mode())
    apply_mode_visuals(view)


def set_window_mode(window, mode):
    for view in window.views():
        view.settings().set(SETTING, mode)
        apply_mode_visuals(view)
    # Active view last so the flag is definitely current for the next keypress.
    active = window.active_view()
    if active:
        active.settings().set(SETTING, mode)
        apply_mode_visuals(active)
    sublime.status_message("Fourcoder modal: " + mode_label(mode))


def run_bound_command(view, command, args):
    args = args or {}
    if command == "_fourcoder_copy":
        view.run_command("fourcoder_copy")
        return
    if command == "_fourcoder_cut":
        view.run_command("fourcoder_cut")
        return
    if command in WINDOW_COMMANDS:
        window = view.window()
        if window:
            window.run_command(command, args)
        return
    view.run_command(command, args)


class FourcoderModalListener(sublime_plugin.EventListener):
    def on_query_context(self, view, key, operator, operand, match_all):
        if key != "fourcoder_navigate":
            return None
        ensure_mode(view)
        navigate = view.settings().get(NAVIGATE_FLAG, False)
        if operator == sublime.OP_EQUAL:
            return navigate == bool(operand)
        if operator == sublime.OP_NOT_EQUAL:
            return navigate != bool(operand)
        return None

    def on_init(self, views):
        for view in views:
            ensure_mode(view)

    def on_activated(self, view):
        # Overlay/panel closed or tab focused again — restore navigate caret.
        ensure_mode(view)

    def on_deactivated(self, view):
        # Goto Anything / panels inherit block_caret from the view; clear it so
        # search fields always get a normal thin caret and insert typing.
        if view.settings().get(NAVIGATE_FLAG):
            view.settings().set("block_caret", False)

    def on_new(self, view):
        # Inherit mode from the window's other views when possible.
        window = view.window()
        mode = default_mode()
        if window:
            for other in window.views():
                if other.id() != view.id() and other.settings().get(SETTING):
                    mode = other.settings().get(SETTING)
                    break
        view.settings().set(SETTING, mode)
        apply_mode_visuals(view)


class FourcoderModalToggleCommand(sublime_plugin.WindowCommand):
    def run(self):
        view = self.window.active_view()
        if not view:
            return
        ensure_mode(view)
        current = view.settings().get(SETTING, default_mode())
        new_mode = MODE_INSERT if current == MODE_NAVIGATE else MODE_NAVIGATE
        set_window_mode(self.window, new_mode)


class FourcoderModalInsertCommand(sublime_plugin.WindowCommand):
    def run(self):
        set_window_mode(self.window, MODE_INSERT)


class FourcoderModalNavigateCommand(sublime_plugin.WindowCommand):
    def run(self):
        set_window_mode(self.window, MODE_NAVIGATE)


class FourcoderCopyCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if all(s.empty() for s in self.view.sel()):
            self.view.run_command(
                "run_macro_file",
                {"file": "res://Packages/User/copy_line.sublime-macro"},
            )
        else:
            self.view.run_command("copy")


class FourcoderCutCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if all(s.empty() for s in self.view.sel()):
            self.view.run_command(
                "run_macro_file",
                {"file": "res://Packages/User/cut_line.sublime-macro"},
            )
        else:
            self.view.run_command("cut")


class FourcoderModalDispatchCommand(sublime_plugin.TextCommand):
    def run(self, edit, key, shift=False):
        key = key.lower()
        entry = BINDINGS.get((key, bool(shift)))
        if not entry:
            return
        command, args = entry
        run_bound_command(self.view, command, args)


def _navigate_context():
    # Never steal keys from Goto Anything, the find/replace bar, etc.
    return [
        {
            "key": "setting.fourcoder_navigate",
            "operator": "equal",
            "operand": True,
        },
        {"key": "overlay_visible", "operator": "equal", "operand": False},
        {"key": "panel_has_focus", "operator": "equal", "operand": False},
    ]


def _build_navigate_keymap():
    entries = [{"keys": ["f5"], "command": "fourcoder_modal_toggle"}]
    for key in TEXT_KEYS:
        entries.append(
            {
                "keys": [key],
                "command": "fourcoder_modal_dispatch",
                "args": {"key": key, "shift": False},
                "context": _navigate_context(),
            }
        )
        entries.append(
            {
                "keys": ["shift+" + key],
                "command": "fourcoder_modal_dispatch",
                "args": {"key": key, "shift": True},
                "context": _navigate_context(),
            }
        )
    return entries


def plugin_loaded():
    sublime.log_message("Fourcoder modal: plugin loaded")
    mode = default_mode()
    for window in sublime.windows():
        set_window_mode(window, mode)
