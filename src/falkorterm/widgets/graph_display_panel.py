from __future__ import annotations

from textual.binding import Binding
from textual.containers import Vertical
from textual.message import Message
from textual.widgets import Checkbox, Label, SelectionList
from textual.widgets.selection_list import Selection

from falkorterm.graph.display import GraphDisplayOptions, toggle_prop
from falkorterm.graph.models import GraphViewModel


class DisplayOptionsChanged(Message):
    """Emitted when graph display options change."""


class GraphDisplayPanel(Vertical):
    """Bottom-right dock for ASCII graph display options."""

    can_focus = True

    BINDINGS = [
        Binding("escape", "close_panel", "Close", show=False),
        Binding("p", "close_panel", "Close", show=False),
    ]

    DEFAULT_CSS = """
    GraphDisplayPanel {
        layer: overlay;
        dock: right;
        width: 34;
        height: 14;
        max-height: 16;
        background: $surface;
        border: tall $primary;
        padding: 0 1;
        display: none;
    }
    GraphDisplayPanel.-open {
        display: block;
    }
    GraphDisplayPanel #display-title {
        text-style: bold;
        color: $text;
    }
    GraphDisplayPanel #display-labels-heading,
    GraphDisplayPanel #display-props-heading {
        color: $text-muted;
        margin-top: 0;
    }
    GraphDisplayPanel SelectionList {
        height: 4;
        min-height: 3;
        border: none;
        background: transparent;
    }
    GraphDisplayPanel #display-show-id {
        height: 1;
        margin-top: 0;
    }
    """

    def __init__(self, *, options: GraphDisplayOptions, **kwargs) -> None:
        super().__init__(**kwargs)
        self._options = options
        self._model: GraphViewModel | None = None
        self._suppress = False

    def compose(self):
        yield Label("display", id="display-title")
        yield Label("labels", id="display-labels-heading")
        yield SelectionList[str](id="display-labels")
        yield Label("props", id="display-props-heading")
        yield SelectionList[str](id="display-props")
        yield Checkbox("show id", value=True, id="display-show-id")

    def is_open(self) -> bool:
        return self.has_class("-open")

    def open_panel(self) -> None:
        self.add_class("-open")
        self.refresh_from_options()
        labels = self.query_one("#display-labels", SelectionList)
        if labels.option_count:
            labels.focus()
        else:
            self.focus()

    def close_panel(self) -> None:
        self.remove_class("-open")

    def action_close_panel(self) -> None:
        self.close_panel()
        parent = self.parent
        if parent is not None and hasattr(parent, "focus"):
            parent.focus()

    def set_model(self, model: GraphViewModel | None) -> None:
        self._model = model
        if model is not None:
            self._options.sync_from_model(model)
        self.refresh_from_options()

    def refresh_from_options(self) -> None:
        self._suppress = True
        try:
            labels_list = self.query_one("#display-labels", SelectionList)
            props_list = self.query_one("#display-props", SelectionList)
            show_id = self.query_one("#display-show-id", Checkbox)

            label_names = sorted(self._options.known_keys_by_label.keys())
            if self._model is not None:
                discovered = {
                    label for node in self._model.nodes for label in node.labels
                }
                label_names = sorted(discovered)

            labels_list.clear_options()
            for label in label_names:
                visible = label not in self._options.hidden_labels
                labels_list.add_option(
                    Selection(f":{label}", label, initial_state=visible)
                )

            if (
                self._options.active_label is None
                or self._options.active_label not in label_names
            ):
                self._options.active_label = label_names[0] if label_names else None

            self._rebuild_props_list(props_list)
            show_id.value = self._options.show_id

            heading = self.query_one("#display-props-heading", Label)
            active = self._options.active_label
            heading.update(f"props (:{active})" if active else "props")
        finally:
            self._suppress = False

    def _rebuild_props_list(self, props_list: SelectionList[str]) -> None:
        props_list.clear_options()
        active = self._options.active_label
        if active is None:
            return
        keys = sorted(self._options.known_keys_by_label.get(active, set()))
        selected = set(self._options.props_by_label.get(active, ()))
        for key in keys:
            props_list.add_option(
                Selection(key, key, initial_state=key in selected)
            )

    def on_selection_list_selection_highlighted(
        self, event: SelectionList.SelectionHighlighted
    ) -> None:
        if self._suppress:
            return
        if event.selection_list.id != "display-labels":
            return
        selection = event.selection
        if selection is None:
            return
        label = str(selection.value)
        if label == self._options.active_label:
            return
        self._options.active_label = label
        props_list = self.query_one("#display-props", SelectionList)
        self._suppress = True
        try:
            self._rebuild_props_list(props_list)
            self.query_one("#display-props-heading", Label).update(
                f"props (:{label})"
            )
        finally:
            self._suppress = False

    def on_selection_list_selected_changed(
        self, event: SelectionList.SelectedChanged
    ) -> None:
        if self._suppress:
            return
        list_id = event.selection_list.id
        selected = set(event.selection_list.selected)

        if list_id == "display-labels":
            all_labels = {
                str(opt.value) for opt in event.selection_list.options
            }
            self._options.hidden_labels = all_labels - selected
            # Keep active_label pointing at a known label.
            if (
                self._options.active_label is None
                or self._options.active_label not in all_labels
            ):
                self._options.active_label = next(iter(sorted(all_labels)), None)
            self.post_message(DisplayOptionsChanged())
            return

        if list_id == "display-props":
            active = self._options.active_label
            if active is None:
                return
            # Apply FIFO via toggle_prop relative to desired set.
            current = list(self._options.props_by_label.get(active, []))
            # Remove unchecked
            for key in list(current):
                if key not in selected:
                    toggle_prop(self._options, active, key)
            # Add newly checked (FIFO if over 3)
            for key in event.selection_list.selected:
                if key not in self._options.props_by_label.get(active, []):
                    toggle_prop(self._options, active, key)
            # Sync UI if FIFO dropped keys
            desired = set(self._options.props_by_label.get(active, []))
            if set(event.selection_list.selected) != desired:
                self._suppress = True
                try:
                    self._rebuild_props_list(event.selection_list)
                finally:
                    self._suppress = False
            self.post_message(DisplayOptionsChanged())

    def on_checkbox_changed(self, event: Checkbox.Changed) -> None:
        if self._suppress or event.checkbox.id != "display-show-id":
            return
        self._options.show_id = event.value
        self.post_message(DisplayOptionsChanged())
