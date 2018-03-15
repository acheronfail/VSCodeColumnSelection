import sublime
import sublime_plugin

def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value

# This is to keep the original anchor as long as we keep making vscode style
# column selections - otherwise clear it.
last_selection = None

# Use an EventListener rather than a ViewEventListener because Sublime Text
# builds below 3155 don't fire the ViewEventListener.on_text_command method.
class ColumnSelectionListener(sublime_plugin.EventListener):
    def on_deactivated(self, view):
        global last_selection
        last_selection = None

    def on_text_command(self, view, name, args):
        global last_selection
        if name != "column_selection":
            last_selection = None

class ColumnSelectionCommand(sublime_plugin.TextCommand):
    # Return true here in order to get mouse event passed to run.
    def want_event(self):
        return True

    # Our actual command.
    def run(self, _edit, event):
        global last_selection
        # Treat the first selection as the primary selection:
        # Sublime Text has no concept of "primary selections", if you make
        # multiple selections and then press `esc` to go back to one selection,
        # then Sublime will always select the first (topmost) selection.
        #
        # This means the functionality may be slightly unexpected when compared
        # to other editors, where for example, the primary selection is:
        #   Atom:       the first selection made
        #   VSCode:     the first selection made
        #   CodeMirror: the last selection made
        #   ACE:        the last selection made
        views_selections = self.view.sel()

        # We save the last selection to better emulate the behaviour of vscode.
        if last_selection is not None:
            primary_selection = last_selection
        else:
            last_selection = primary_selection = views_selections[0]

        # Use layout coordinates to find the start and end of each selection on
        # each line. It's easier just to use `row`s and `col`s, but that won't
        # be accurate for emoji and other non-monospaced characters.
        # Think of `(x1, y1)` and `(x2, y2)` defining the edges of a rectangle
        # which is our selection.
        (x1, y1) = self.view.text_to_layout(primary_selection.a)
        (x2, y2) = self.view.window_to_layout((event.get('x'), event.get('y')))
        start_row = self.view.rowcol(primary_selection.a)[0]
        click_point = self.view.layout_to_text((x2, y2))
        click_row = self.view.rowcol(click_point)[0]

        # Check if we should put a selection of every line.
        all_empty = True
        skipped_lines = []

        # limit for ignoring selections - used to allow for the slightly off
        # measurements that are present when there are non-monospaced characters.
        limit = self.view.em_width() / 2

        # Iterate through lines (from top to bottom) and create selection regions.
        selections = []
        first, last = min(start_row, click_row), max(start_row, click_row)
        for row in range(first, last + 1):
            # This line's region.
            line = self.view.line(self.view.text_point(row, 0))

            # Just remember the line's region if it's empty and continue.
            if line.empty():
                skipped_lines.append(line)
                continue

            # Find the first & last char at the start & click points on this line.
            line_y = self.view.text_to_layout(line.a)[1]
            a = clamp(self.view.layout_to_text((x1, line_y)), line.a, line.b)
            b = clamp(self.view.layout_to_text((x2, line_y)), line.a, line.b)
            region = sublime.Region(a, b)

            # Skip lines that don't reach inside the column selection.
            point = self.view.text_to_layout(a)[0]
            if x1 < x2 and point < x1 - limit or x1 > x2 and point < x2 - limit:
                skipped_lines.append(region)
                continue

            if all_empty and not region.empty():
                all_empty = False

            # Add region to selections.
            selections.append(region)

        # Place a selection on every line (even if it's not within the rect) if:
        #   the starting line is an empty line, or
        #   all of the selected regions are empty.
        if self.view.line(primary_selection).empty() or all_empty:
            selections.extend(skipped_lines)

        # Replace the view's selections, if we have any to add.
        if len(selections):
            views_selections.clear()
            views_selections.add_all(selections)
