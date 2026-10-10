import sublime
import sublime_plugin


def _line_is_blank(view, row):
    """True if the line is empty or only whitespace."""
    region = view.line(view.text_point(row, 0))
    return view.substr(region).strip() == ""


class MoveToBlankLineCommand(sublime_plugin.TextCommand):
    """Like move by empty_line stops, but whitespace-only lines count as blank."""

    def run(self, edit, forward=True, extend=False):
        view = self.view
        last_row = view.rowcol(view.size())[0]
        selections = []

        for region in view.sel():
            row, _ = view.rowcol(region.b)

            if forward:
                target = row + 1
                while target <= last_row and not _line_is_blank(view, target):
                    target += 1
                if target > last_row:
                    target = last_row
            else:
                target = row - 1
                while target >= 0 and not _line_is_blank(view, target):
                    target -= 1
                if target < 0:
                    target = 0

            dest = view.text_point(target, 0)
            if extend:
                selections.append(sublime.Region(region.a, dest))
            else:
                selections.append(sublime.Region(dest))

        view.sel().clear()
        for sel in selections:
            view.sel().add(sel)
        if selections:
            view.show(selections[-1].b)
