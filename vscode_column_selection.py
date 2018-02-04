import sublime
import sublime_plugin

def clamp(value, low, high):
    if value < low:
        return low
    if value > high:
        return high
    return value

class ColumnSelectionCommand(sublime_plugin.TextCommand):
    def run(self, _edit, event):
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
        primary_selection = views_selections[0]
        anchor = self.view.rowcol(primary_selection.a)

        # Calculate head position from click event.
        window_vector = (event.get('x'), event.get('y'))
        head_point = self.view.window_to_text(window_vector)
        head_row = self.view.rowcol(head_point)[0]
        layout_vector = self.view.window_to_layout(window_vector)
        head = (head_row, layout_vector[0] // self.view.em_width())

        # Place a selection on every line if:
        #   anchor.col == head.col, or
        #   anchor line is empty.
        col_start, col_end = anchor[1], head[1]
        all_lines = col_start == col_end or self.view.line(primary_selection).empty()

        # Iterate through lines and create selection regions.
        selections = []
        start, end = min(anchor[0], head[0]), max(anchor[0], head[0])
        for row in range(start, end + 1):
            line = self.view.line(self.view.text_point(row, 0))

            # Either skip empty lines, or add a selection if `all_lines` is set.
            if line.empty():
                if all_lines:
                    selections.append(line.a)
                continue

            # Find text points for selection.
            a = clamp(self.view.text_point(row, col_start), line.a, line.b)
            b = clamp(self.view.text_point(row, col_end), line.a, line.b)

            # Ignore lines that don't reach inside the column selection.
            if col_start < col_end and self.view.rowcol(a)[1] < col_start:
                continue
            elif col_start > col_end and self.view.rowcol(a)[1] < col_end:
                continue

            selections.append(sublime.Region(a, b))

        # Replace the view's selections, if we have any to add.
        if len(selections):
            views_selections.clear()
            views_selections.add_all(selections)


    # Return true here in order to get mouse event passed to run
    def want_event(self):
        return True
