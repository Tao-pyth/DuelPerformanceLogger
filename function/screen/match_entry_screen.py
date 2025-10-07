"""Match entry screen logic with UI defined in KV files."""

from __future__ import annotations

from typing import Optional

from kivy.properties import (
    BooleanProperty,
    ListProperty,
    ObjectProperty,
    StringProperty,
)
from kivymd.toast import toast
from kivymd.uix.menu import MDDropdownMenu

from function import DatabaseError
from function.cmn_app_state import get_app_state
from function.cmn_logger import log_db_error
from function.cmn_resources import get_text

from .base import BaseManagedScreen


def _normalize_turn_options():
    """設定からターン選択肢を読み込み、(ラベル, 値) へ整形する."""

    raw = get_text("match_entry.turn_options")
    options: list[tuple[str, bool]] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                label = str(item.get("label", ""))
                value = item.get("value")
                if label:
                    options.append((label, bool(value)))
            else:
                label = str(item)
                value = True if not options else False
                options.append((label, value))
    if not options:
        options = [("先攻", True), ("後攻", False)]
    return options


def _normalize_result_options():
    """設定から勝敗選択肢を読み込み、(ラベル, 値) に整形する."""

    raw = get_text("match_entry.result_options")
    options: list[tuple[str, int]] = []
    if isinstance(raw, list):
        for item in raw:
            if isinstance(item, dict):
                label = str(item.get("label", ""))
                value = item.get("value")
                if label:
                    try:
                        options.append((label, int(value)))
                    except (TypeError, ValueError):
                        continue
            else:
                label = str(item)
                mapped = 1 if not options else -1
                options.append((label, mapped))
    if not options:
        options = [("勝ち", 1), ("引き分け", 0), ("負け", -1)]
    return options


TURN_OPTIONS = _normalize_turn_options()
TURN_VALUE_TO_LABEL = {value: label for label, value in TURN_OPTIONS}
RESULT_OPTIONS = _normalize_result_options()
RESULT_VALUE_TO_LABEL = {value: label for label, value in RESULT_OPTIONS}


class MatchEntryScreen(BaseManagedScreen):
    """Screen that allows recording match results."""

    can_save = BooleanProperty(False)
    busy = BooleanProperty(False)
    title = StringProperty("")
    status_message = StringProperty("")
    match_info = StringProperty("")
    last_record_text = StringProperty("")
    last_record_available = BooleanProperty(False)
    turn = ObjectProperty(None, allownone=True)
    result = ObjectProperty(None, allownone=True)
    turn_options = ListProperty()
    result_options = ListProperty()

    screen_mode = "normal"

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.turn_options = list(TURN_OPTIONS)
        self.result_options = list(RESULT_OPTIONS)
        self._opponent_menu: Optional[MDDropdownMenu] = None
        self.last_record_data: Optional[dict] = None
        self._selected_bg_color = (0.18, 0.36, 0.58, 1)
        self._selected_text_color = (1, 1, 1, 1)
        self._idle_bg_color = (0.93, 0.96, 0.98, 1)
        self._idle_text_color = (0.18, 0.36, 0.58, 1)

    def on_kv_post(self, base_widget):
        super().on_kv_post(base_widget)
        self.title = get_text("match_entry.header_title")
        self.status_message = get_text("match_entry.status_default")
        self.match_info = ""
        self.last_record_text = get_text("match_entry.last_record_empty")

    def on_pre_enter(self, *args):  # noqa: D401 - Kivy hook
        super().on_pre_enter(*args)
        self.turn = None
        self.result = None
        self._recalc()
        self.refresh_opponent_menu()

        app = get_app_state()
        settings = getattr(app, "current_match_settings", None)
        if not settings:
            self._set_status_message(get_text("match_entry.status_missing_setup"))
            self._set_match_info(None, None)
            self.last_record_data = None
            self.last_record_text = get_text("match_entry.last_record_empty")
            self.last_record_available = False
            return

        self._update_status_summary(app.current_match_count, settings["deck_name"])
        self.reset_inputs(focus_opponent=True)
        self._load_last_record()

    def on_leave(self, *args):  # noqa: D401 - Kivy hook
        super().on_leave(*args)
        self._dismiss_opponent_menu()

    # ------------------------------------------------------------------
    # UI interaction helpers
    # ------------------------------------------------------------------
    def set_turn(self, value):
        """Update the selected turn option."""

        self.turn = value
        self._recalc()

    def set_result(self, value):
        """Update the selected match result."""

        self.result = value
        self._recalc()

    def reset_inputs(self, *, focus_opponent: bool = False) -> None:
        """Clear text fields and reset selections."""

        opponent = self.ids.get("opponent")
        keywords = self.ids.get("keywords")
        if opponent is not None:
            opponent.text = ""
            if focus_opponent:
                opponent.focus = True
        if keywords is not None:
            keywords.text = ""
        self.turn = None
        self.result = None
        self._dismiss_opponent_menu()
        self._recalc()

    def clear_inputs(self):
        """Callback for the clear button."""

        self.reset_inputs(focus_opponent=True)

    def is_selected(self, current, value):
        """Return whether the given option is selected."""

        return current == value

    def button_bg_color(self, current, value):
        """Provide background color for option buttons."""

        return self._selected_bg_color if current == value else self._idle_bg_color

    def button_text_color(self, current, value):
        """Provide text color for option buttons."""

        return (
            self._selected_text_color
            if current == value
            else self._idle_text_color
        )

    # ------------------------------------------------------------------
    # Menu handling
    # ------------------------------------------------------------------
    def refresh_opponent_menu(self):
        """Recreate the dropdown menu for opponent deck names."""

        if self._opponent_menu:
            self._opponent_menu.dismiss()
            self._opponent_menu = None

        button = self.ids.get("opponent_menu_button")
        if button is None:
            return

        app = get_app_state()
        options = getattr(app, "opponent_decks", []) or []

        menu_items = []
        for option in options:
            menu_items.append(
                {
                    "viewclass": "OneLineListItem",
                    "text": option,
                    "on_release": lambda value=option: self.set_opponent_from_menu(value),
                }
            )

        if not options:
            menu_items.append(
                {
                    "viewclass": "OneLineListItem",
                    "text": get_text("match_entry.opponent_menu_empty"),
                    "disabled": True,
                    "on_release": lambda *_: None,
                }
            )

        menu_items.append(
            {
                "viewclass": "OneLineListItem",
                "text": get_text("match_entry.opponent_manual_entry"),
                "on_release": lambda *_: self._manual_input_opponent(),
            }
        )

        self._opponent_menu = MDDropdownMenu(
            caller=button,
            items=menu_items,
            width_mult=4,
        )

    def open_opponent_menu(self):
        """Open the dropdown menu when the button is pressed."""

        if self._opponent_menu is None:
            self.refresh_opponent_menu()
        if self._opponent_menu is not None:
            self._opponent_menu.caller = self.ids.get("opponent_menu_button")
            self._opponent_menu.open()

    def _manual_input_opponent(self):
        """Switch focus to manual opponent entry."""

        opponent = self.ids.get("opponent")
        if opponent is not None:
            opponent.focus = True
            opponent.text = ""
        self._dismiss_opponent_menu()

    def _dismiss_opponent_menu(self):
        if self._opponent_menu:
            self._opponent_menu.dismiss()
            self._opponent_menu = None

    def set_opponent_from_menu(self, value: str):
        """Populate the opponent field from the selected menu item."""

        opponent = self.ids.get("opponent")
        if opponent is not None:
            opponent.text = value
        self._dismiss_opponent_menu()
        self._recalc()

    # ------------------------------------------------------------------
    # Record handling
    # ------------------------------------------------------------------
    def _recalc(self):
        """Recalculate whether the save button should be enabled."""

        opponent = self.ids.get("opponent")
        opponent_text = opponent.text.strip() if opponent is not None else ""
        self.can_save = bool(opponent_text and self.result is not None and self.turn is not None and not self.busy)

    def save(self):
        """Validate inputs and record the match."""

        if not self.can_save or self.busy:
            return

        app = get_app_state()
        settings = getattr(app, "current_match_settings", None)
        if not settings:
            toast(get_text("match_entry.toast_missing_setup"))
            return

        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        opponent = self.ids.get("opponent")
        keywords = self.ids.get("keywords")
        opponent_text = opponent.text.strip() if opponent is not None else ""
        keywords_text = keywords.text if keywords is not None else ""

        record = {
            "match_no": app.current_match_count,
            "deck_name": settings["deck_name"],
            "turn": self.turn,
            "opponent_deck": opponent_text,
            "keywords": [
                kw.strip()
                for kw in keywords_text.split(",")
                if kw.strip()
            ],
            "result": self.result,
        }

        self.busy = True
        self.can_save = False
        error_occurred = False
        try:
            db.record_match(record)
        except DatabaseError as exc:
            log_db_error("Failed to record match", exc, record=record)
            toast(get_text("common.db_error"))
            error_occurred = True
        finally:
            self.busy = False

        if error_occurred:
            self._recalc()
            return

        app.match_records = db.fetch_matches()
        app.opponent_decks = db.fetch_opponent_decks()
        self.refresh_opponent_menu()

        app.current_match_count += 1
        settings["count"] = app.current_match_count
        self._update_status_summary(app.current_match_count, settings["deck_name"])

        self.reset_inputs(focus_opponent=True)
        self._load_last_record()
        toast(get_text("match_entry.toast_recorded"))

    def copy_last_record(self):
        """Copy last record values into the input fields."""

        if not self.last_record_data:
            return

        opponent = self.ids.get("opponent")
        keywords = self.ids.get("keywords")
        if opponent is not None:
            opponent.text = self.last_record_data.get("opponent_deck", "")
        if keywords is not None:
            keywords.text = ", ".join(self.last_record_data.get("keywords") or [])
        toast(get_text("match_entry.toast_copied_previous"))
        self._recalc()

    def _load_last_record(self):
        """Load the latest saved record and update the summary."""

        app = get_app_state()
        settings = getattr(app, "current_match_settings", None)
        db = getattr(app, "db", None)
        if db is None or not settings:
            self.last_record_data = None
            self.last_record_text = get_text("match_entry.last_record_empty")
            self.last_record_available = False
            return

        last_record = db.fetch_last_match(settings["deck_name"])
        if not last_record:
            self.last_record_data = None
            self.last_record_text = get_text("match_entry.last_record_empty")
            self.last_record_available = False
            return

        self.last_record_data = last_record
        keywords = last_record.get("keywords") or []
        keywords_text = (
            ", ".join(keywords)
            if keywords
            else get_text("match_entry.last_record_no_keywords")
        )
        opponent_text = (
            last_record.get("opponent_deck")
            or get_text("match_entry.last_record_no_opponent")
        )
        turn_value = bool(last_record.get("turn"))
        result_value = int(last_record.get("result"))
        turn_label = TURN_VALUE_TO_LABEL.get(turn_value, str(last_record.get("turn")))
        result_label = RESULT_VALUE_TO_LABEL.get(
            result_value, str(last_record.get("result"))
        )
        self.last_record_text = get_text(
            "match_entry.last_record_template"
        ).format(
            match_no=last_record.get("match_no"),
            turn=turn_label,
            result=result_label,
            opponent=opponent_text,
            keywords=keywords_text,
        )
        self.last_record_available = True

    # ------------------------------------------------------------------
    # Status helpers
    # ------------------------------------------------------------------
    def _update_status_summary(self, count: int, deck_name: str) -> None:
        self._set_match_info(count, deck_name)

    def _set_status_message(self, message: str) -> None:
        self.status_message = message

    def _set_match_info(self, count: Optional[int], deck_name: Optional[str]) -> None:
        if count is None or not deck_name:
            self.match_info = ""
        else:
            self.match_info = f"#{count} {deck_name}"

    # ------------------------------------------------------------------
    # Navigation helpers
    # ------------------------------------------------------------------
    def go_to_menu(self):
        """Navigate back to the menu screen."""

        self.change_screen("menu")

    def go_to_setup(self):
        """Navigate to the match setup screen."""

        self.change_screen("match_setup")


class MatchEntryBroadcastScreen(MatchEntryScreen):
    screen_mode = "broadcast"


__all__ = [
    "MatchEntryScreen",
    "MatchEntryBroadcastScreen",
    "TURN_OPTIONS",
    "TURN_VALUE_TO_LABEL",
    "RESULT_OPTIONS",
    "RESULT_VALUE_TO_LABEL",
]
