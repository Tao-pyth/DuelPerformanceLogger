"""Match entry screen and helper utilities."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from kivy.clock import Clock
from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivymd.toast import toast
from kivymd.uix.anchorlayout import MDAnchorLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDRectangleFlatButton
from kivymd.uix.card import MDCard
from kivymd.uix.button import MDIconButton  
from kivymd.uix.label import MDLabel
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.textfield import MDTextField

from function import DatabaseError
from function.cmn_app_state import get_app_state
from function.cmn_logger import log_db_error
from function.cmn_resources import get_text

from .base import BaseManagedScreen


def _normalize_turn_options():
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
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.turn_choice: Optional[bool] = None
        self.result_choice: Optional[int] = None
        self.turn_buttons: list[MDRectangleFlatButton] = []
        self.result_buttons: list[MDRectangleFlatButton] = []
        self.last_record_data = None
        self._clock_event = None
        self._active_mode = "normal"

        (
            self.normal_root,
            normal_content_anchor,
            normal_action_anchor,
        ) = self._create_scaffold(
            get_text("match_entry.header_title"),
            lambda: self.change_screen("match_setup"),
            lambda: self.change_screen("menu"),
        )

        self.clock_label = MDLabel(
            text=self._get_current_time_text(),
            halign="center",
            font_style="H5",
        )
        self._configure_label(self.clock_label, wrap=False)

        self.match_info_label = MDLabel(
            text="",
            halign="center",
            font_style="Subtitle1",
        )
        self._configure_label(self.match_info_label)

        self.status_label = MDLabel(
            text=get_text("match_entry.status_default"),
            halign="center",
            font_style="H5",
        )
        self._configure_label(self.status_label)

        self.opponent_field = MDTextField(
            hint_text=get_text("match_entry.opponent_hint"),
        )
        self.opponent_menu_button = MDIconButton(
            icon="chevron-down",
            on_release=lambda *_: self.open_opponent_menu(),
        )
        self.opponent_menu_button.theme_text_color = "Custom"
        self.opponent_menu_button.text_color = (0.18, 0.36, 0.58, 1)
        self.opponent_menu_button.size_hint = (None, None)
        self.opponent_menu_button.height = dp(48)
        self.opponent_menu = None

        self.keyword_field = MDTextField(
            hint_text=get_text("match_entry.keyword_hint"),
            multiline=True,
        )
        self.keyword_field.size_hint = (1, None)
        self.keyword_field.height = dp(72)

        self.normal_scroll = ScrollView(size_hint=(0.95, 0.95))
        self.normal_content = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint_y=None,
        )
        self.normal_content.bind(minimum_height=self.normal_content.setter("height"))
        self.normal_scroll.add_widget(self.normal_content)
        normal_content_anchor.add_widget(self.normal_scroll)

        self.last_record_card = self._build_last_record_card()

        self.turn_prompt_label = MDLabel(
            text=get_text("match_entry.turn_prompt"),
            theme_text_color="Secondary",
        )
        self._configure_label(self.turn_prompt_label)
        self.result_prompt_label = MDLabel(
            text=get_text("match_entry.result_prompt"),
            theme_text_color="Secondary",
        )
        self._configure_label(self.result_prompt_label)

        self.turn_container_normal = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            size_hint_y=None,
            height=dp(48),
        )
        self._populate_toggle_buttons(
            self.turn_container_normal,
            TURN_OPTIONS,
            self.turn_buttons,
            self.set_turn_choice,
        )

        self.opponent_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(72),
        )
        self.opponent_field.size_hint_y = None
        self.opponent_field.height = dp(72)
        self.opponent_row.add_widget(self.opponent_field)
        self.opponent_row.add_widget(self.opponent_menu_button)

        self.opponent_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            size_hint_y=None,
        )
        self.opponent_section.bind(
            minimum_height=self.opponent_section.setter("height")
        )
        self.opponent_section.add_widget(self.opponent_row)
        self.opponent_section.add_widget(self.keyword_field)

        self.result_container_normal = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            size_hint_y=None,
            height=dp(48),
        )
        self._populate_toggle_buttons(
            self.result_container_normal,
            RESULT_OPTIONS,
            self.result_buttons,
            self.set_result_choice,
        )

        self.normal_content_widgets = [
            self.clock_label,
            self.match_info_label,
            self.status_label,
            self.last_record_card,
            self.turn_prompt_label,
            self.turn_container_normal,
            self.opponent_section,
            self.result_prompt_label,
            self.result_container_normal,
        ]
        for widget in self.normal_content_widgets:
            self.normal_content.add_widget(widget)

        self.quick_actions = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            size_hint=(0.85, None),
            height=dp(48),
        )
        self.clear_button = MDFlatButton(
            text=get_text("match_entry.clear_button"),
            on_press=lambda *_: self.reset_inputs(focus_opponent=True),
        )
        self.record_button = MDRaisedButton(
            text=get_text("match_entry.record_button"),
            on_press=lambda *_: self.submit_match(),
        )
        self.back_button = MDFlatButton(
            text=get_text("match_entry.back_button"),
            on_press=lambda *_: self.change_screen("match_setup"),
        )
        for button in (self.clear_button, self.record_button, self.back_button):
            button.size_hint = (1, None)
            button.height = dp(48)
        self.quick_actions.add_widget(self.clear_button)
        self.quick_actions.add_widget(self.record_button)
        self.quick_actions.add_widget(self.back_button)
        normal_action_anchor.add_widget(self.quick_actions)
        self.quick_action_buttons = [
            self.clear_button,
            self.record_button,
            self.back_button,
        ]

        self.broadcast_layout = self._build_broadcast_layout()
        self._update_toggle_style(self.turn_buttons, None)
        self._update_toggle_style(self.result_buttons, None)

    def _build_last_record_card(self):
        """Create a summary card showing the latest saved match."""

        card = MDCard(
            orientation="vertical",
            padding=(dp(16), dp(16), dp(16), dp(16)),
            size_hint=(1, None),
            radius=[16, 16, 16, 16],
        )
        card.spacing = dp(12)

        card.add_widget(
            MDLabel(
                text=get_text("match_entry.last_record_title"),
                font_style="Subtitle1",
            )
        )

        self.last_record_label = MDLabel(
            text=get_text("match_entry.last_record_empty"),
            theme_text_color="Secondary",
        )
        self._configure_label(self.last_record_label)
        card.add_widget(self.last_record_label)

        action_row = MDBoxLayout(spacing=dp(8), size_hint_y=None, height=dp(36))
        action_row.add_widget(Widget())
        self.copy_last_button = MDFlatButton(
            text=get_text("match_entry.copy_last_button"),
            on_press=lambda *_: self.copy_last_record(),
            disabled=True,
        )
        self.copy_last_button.size_hint = (None, None)
        self.copy_last_button.height = dp(36)
        action_row.add_widget(self.copy_last_button)
        card.add_widget(action_row)

        return card

    @staticmethod
    def _configure_label(label: MDLabel, *, wrap: bool = True) -> None:
        label.size_hint_y = None

        if wrap:
            def _update_text_size(instance, _value):
                instance.text_size = (instance.width, None)

            label.bind(width=_update_text_size)
            _update_text_size(label, label.width)

        label.bind(
            texture_size=lambda instance, value: setattr(instance, "height", value[1])
        )
        if hasattr(label, "texture_update"):
            label.texture_update()
        label.height = getattr(label, "texture_size", (0, 0))[1]

    def _populate_toggle_buttons(
        self,
        container: MDBoxLayout,
        options: list[tuple[str, object]],
        collection: list[MDRectangleFlatButton],
        callback,
    ) -> None:
        app = get_app_state()
        primary_color = getattr(app.theme_cls, "primary_color", (0.2, 0.6, 0.86, 1))
        neutral_line = (0.7, 0.7, 0.7, 1)

        for label, value in options:
            button = MDRectangleFlatButton(text=label)
            button.size_hint = (1, None)
            button.height = dp(48)
            button.md_bg_color = (1, 1, 1, 1)
            button.text_color = primary_color
            button.line_color = neutral_line
            button._toggle_value = value

            def make_callback(choice):
                return lambda *_: callback(choice)

            button.bind(on_release=make_callback(value))
            container.add_widget(button)
            collection.append(button)

    def _ensure_normal_content_order(self) -> None:
        for widget in self.normal_content_widgets:
            self._remove_from_parent(widget)
        for widget in self.normal_content_widgets:
            self.normal_content.add_widget(widget)

    def _build_broadcast_layout(self) -> MDBoxLayout:
        layout = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            padding=(dp(12), dp(12), dp(12), dp(12)),
        )

        self.broadcast_nav_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=1,
        )
        for icon, callback in (
            ("home", lambda *_: self.change_screen("menu")),
            ("arrow-left", lambda *_: self.change_screen("match_setup")),
        ):
            button = MDIconButton(icon=icon, on_release=callback)
            button.theme_text_color = "Custom"
            button.text_color = (0.18, 0.36, 0.58, 1)
            button.size_hint = (None, None)
            button.height = dp(48)
            button.width = dp(48)
            self.broadcast_nav_section.add_widget(button)
        layout.add_widget(self.broadcast_nav_section)

        self.broadcast_time_section = MDAnchorLayout(
            size_hint_x=4, anchor_x="center", anchor_y="center"
        )
        time_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint=(1, None),
            height=dp(96),
        )
        time_box.bind(minimum_height=time_box.setter("height"))
        self.broadcast_clock_label = MDLabel(
            text=self._get_current_time_text(),
            halign="center",
            font_style="H5",
        )
        self._configure_label(self.broadcast_clock_label, wrap=False)
        self.broadcast_match_info_label = MDLabel(
            text="",
            halign="center",
            font_style="Subtitle1",
        )
        self._configure_label(self.broadcast_match_info_label)
        time_box.add_widget(self.broadcast_clock_label)
        time_box.add_widget(self.broadcast_match_info_label)
        self.broadcast_time_section.add_widget(time_box)
        layout.add_widget(self.broadcast_time_section)

        self.turn_container_broadcast = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=1,
        )
        self._populate_toggle_buttons(
            self.turn_container_broadcast,
            TURN_OPTIONS,
            self.turn_buttons,
            self.set_turn_choice,
        )
        layout.add_widget(self.turn_container_broadcast)

        self.broadcast_deck_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=1,
        )
        self.broadcast_status_label = MDLabel(
            text=get_text("match_entry.status_default"),
            halign="center",
            font_style="Subtitle1",
        )
        self._configure_label(self.broadcast_status_label)
        self.broadcast_deck_section.add_widget(self.broadcast_status_label)
        layout.add_widget(self.broadcast_deck_section)

        self.result_container_broadcast = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=1,
        )
        self._populate_toggle_buttons(
            self.result_container_broadcast,
            RESULT_OPTIONS,
            self.result_buttons,
            self.set_result_choice,
        )
        layout.add_widget(self.result_container_broadcast)

        self.broadcast_actions_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=1,
        )
        layout.add_widget(self.broadcast_actions_section)

        self.broadcast_record_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=1,
        )
        layout.add_widget(self.broadcast_record_section)

        return layout

    @staticmethod
    def _remove_from_parent(widget):
        parent = widget.parent
        if parent is not None:
            parent.remove_widget(widget)

    def _load_last_record(self):
        """Fetch and display the most recent record for the selected deck."""

        app = get_app_state()
        settings = getattr(app, "current_match_settings", None)
        db = getattr(app, "db", None)

        if db is None or not settings:
            self.last_record_data = None
            self.last_record_label.text = get_text("match_entry.last_record_empty")
            if hasattr(self, "copy_last_button"):
                self.copy_last_button.disabled = True
            return

        last_record = db.fetch_last_match(settings["deck_name"])
        if not last_record:
            self.last_record_data = None
            self.last_record_label.text = get_text("match_entry.last_record_empty")
            self.copy_last_button.disabled = True
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
        self.last_record_label.text = get_text(
            "match_entry.last_record_template"
        ).format(
            match_no=last_record.get("match_no"),
            turn=turn_label,
            result=result_label,
            opponent=opponent_text,
            keywords=keywords_text,
        )
        self.copy_last_button.disabled = False

    def copy_last_record(self):
        """Copy the previously stored opponent information into the fields."""

        if not self.last_record_data:
            return

        self.opponent_field.text = self.last_record_data.get("opponent_deck", "")
        keywords = self.last_record_data.get("keywords") or []
        self.keyword_field.text = ", ".join(keywords)
        toast(get_text("match_entry.toast_copied_previous"))

    def refresh_opponent_menu(self):
        """対戦相手デッキ名のドロップダウン候補を再構築する."""

        if self.opponent_menu:
            self.opponent_menu.dismiss()
            self.opponent_menu = None

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

        self.opponent_menu = MDDropdownMenu(
            caller=self.opponent_menu_button,
            items=menu_items,
            width_mult=4,
        )

    def open_opponent_menu(self):
        """プルダウンメニューを開く。必要に応じて再生成する。"""

        if self.opponent_menu is None:
            self.refresh_opponent_menu()
        if self.opponent_menu:
            self.opponent_menu.caller = self.opponent_menu_button
            self.opponent_menu.open()

    def _dismiss_opponent_menu(self):
        if self.opponent_menu:
            self.opponent_menu.dismiss()

    def set_opponent_from_menu(self, value: str):
        """メニューで選択されたデッキ名を入力欄へ反映する."""

        self.opponent_field.text = value
        self._dismiss_opponent_menu()

    def _manual_input_opponent(self):
        """手入力に切り替えるメニュー項目の処理."""

        self._dismiss_opponent_menu()
        self.opponent_field.focus = True
        self.opponent_field.text = ""

    def _update_toggle_style(self, buttons, selected_value):
        app = get_app_state()
        primary = getattr(app.theme_cls, "primary_color", (0.2, 0.6, 0.86, 1))
        highlight = (0.86, 0.16, 0.16, 1)
        neutral_line = (0.7, 0.7, 0.7, 1)

        for button in buttons:
            value = getattr(button, "_toggle_value", None)
            if value == selected_value:
                button.line_color = highlight
                button.text_color = highlight
                button.md_bg_color = (1, 0.93, 0.93, 1)
            else:
                button.line_color = neutral_line
                button.text_color = primary
                button.md_bg_color = (1, 1, 1, 1)

    def _apply_mode_layout(self, mode: str) -> None:
        self._active_mode = mode
        if mode == "broadcast":
            self._show_broadcast_layout()
        else:
            self._show_normal_layout()
        self._update_match_info_visibility(mode)

    def _show_broadcast_layout(self) -> None:
        if self.normal_root.parent:
            self.remove_widget(self.normal_root)
        if not self.broadcast_layout.parent:
            self.add_widget(self.broadcast_layout)

        self.broadcast_deck_section.clear_widgets()
        self.broadcast_deck_section.add_widget(self.broadcast_status_label)
        self._remove_from_parent(self.opponent_section)
        self.broadcast_deck_section.add_widget(self.opponent_section)

        self.broadcast_actions_section.clear_widgets()
        for button in (self.clear_button, self.back_button):
            self._remove_from_parent(button)
            button.size_hint = (1, None)
            button.height = dp(48)
            self.broadcast_actions_section.add_widget(button)

        self.broadcast_record_section.clear_widgets()
        self._remove_from_parent(self.record_button)
        self.record_button.size_hint = (1, None)
        self.record_button.height = dp(48)
        self.broadcast_record_section.add_widget(self.record_button)

    def _show_normal_layout(self) -> None:
        if self.broadcast_layout.parent:
            self.remove_widget(self.broadcast_layout)
        if not self.normal_root.parent:
            self.add_widget(self.normal_root)

        self._remove_from_parent(self.opponent_section)
        self._ensure_normal_content_order()

        self.broadcast_actions_section.clear_widgets()
        self.broadcast_record_section.clear_widgets()

        self.quick_actions.clear_widgets()
        for button in (self.clear_button, self.record_button, self.back_button):
            self._remove_from_parent(button)
            button.size_hint = (1, None)
            button.height = dp(48)
            self.quick_actions.add_widget(button)

    def _update_status_summary(self, count: int, deck_name: str) -> None:
        summary = get_text("match_entry.status_summary").format(
            count=count,
            deck_name=deck_name,
        )
        self.status_label.text = summary
        if hasattr(self, "broadcast_status_label"):
            self.broadcast_status_label.text = summary
        self._set_match_info(count, deck_name)

    def _set_status_message(self, message: str) -> None:
        self.status_label.text = message
        if hasattr(self, "broadcast_status_label"):
            self.broadcast_status_label.text = message

    def _set_match_info(self, count: int | None, deck_name: str | None) -> None:
        if count is None or not deck_name:
            info_text = ""
        else:
            info_text = f"#{count} {deck_name}"
        if hasattr(self, "match_info_label"):
            self.match_info_label.text = info_text
        if hasattr(self, "broadcast_match_info_label"):
            self.broadcast_match_info_label.text = info_text
        self._update_match_info_visibility(self._active_mode)

    def _update_match_info_visibility(self, mode: str) -> None:
        if hasattr(self, "broadcast_match_info_label"):
            if mode == "broadcast":
                self.broadcast_match_info_label.opacity = 0
                self.broadcast_match_info_label.height = 0
            else:
                self.broadcast_match_info_label.opacity = 1
                if hasattr(self.broadcast_match_info_label, "texture_update"):
                    self.broadcast_match_info_label.texture_update()
                self.broadcast_match_info_label.height = (
                    getattr(self.broadcast_match_info_label, "texture_size", (0, 0))[1]
                )

    def set_turn_choice(self, choice):
        # 選択されたボタンのみアクティブ状態にする
        self.turn_choice = choice
        self._update_toggle_style(self.turn_buttons, choice)

    def set_result_choice(self, choice):
        # 勝敗選択も同様にアクティブ表示を切り替える
        self.result_choice = choice
        self._update_toggle_style(self.result_buttons, choice)

    def submit_match(self):
        app = get_app_state()
        settings = getattr(app, "current_match_settings", None)
        if not settings:
            toast(get_text("match_entry.toast_missing_setup"))
            return

        if self.turn_choice is None:
            toast(get_text("match_entry.toast_select_turn"))
            return

        if self.result_choice is None:
            toast(get_text("match_entry.toast_select_result"))
            return

        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        record = {
            "match_no": app.current_match_count,
            "deck_name": settings["deck_name"],
            "turn": self.turn_choice,
            "opponent_deck": self.opponent_field.text.strip(),
            "keywords": [
                kw.strip()
                for kw in self.keyword_field.text.split(",")
                if kw.strip()
            ],
            "result": self.result_choice,
        }

        try:
            db.record_match(record)
        except DatabaseError as exc:
            log_db_error("Failed to record match", exc, record=record)
            toast(get_text("common.db_error"))
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

    def reset_inputs(self, focus_opponent: bool = False):
        # トグルボタンとテキストフィールドを初期状態に戻す
        self.turn_choice = None
        self.result_choice = None
        self._update_toggle_style(self.turn_buttons, None)
        self._update_toggle_style(self.result_buttons, None)
        self._dismiss_opponent_menu()
        self.opponent_field.text = ""
        self.keyword_field.text = ""
        if focus_opponent:
            self.opponent_field.focus = True

    def on_pre_enter(self):
        self._start_clock()
        app = get_app_state()
        mode = getattr(app, "ui_mode", "normal")
        self._apply_mode_layout(mode)
        self._sync_window_size(mode)
        settings = getattr(app, "current_match_settings", None)
        self.refresh_opponent_menu()
        if not settings:
            message = get_text("match_entry.status_missing_setup")
            self._set_status_message(message)
            self._set_match_info(None, None)
            self.last_record_data = None
            if hasattr(self, "last_record_label"):
                self.last_record_label.text = get_text("match_entry.last_record_empty")
            if hasattr(self, "copy_last_button"):
                self.copy_last_button.disabled = True
            return

        self._update_status_summary(app.current_match_count, settings["deck_name"])
        self.reset_inputs(focus_opponent=True)
        self._load_last_record()

    def on_leave(self):
        self._stop_clock()
        app = get_app_state()
        if getattr(app, "ui_mode", "normal") != "broadcast":
            default_size = getattr(app, "default_window_size", None)
            if default_size:
                Window.size = default_size

    def _get_current_time_text(self) -> str:
        return datetime.now().strftime("%Y/%m/%d %H:%M:%S")

    def _update_clock(self, *_):
        current = self._get_current_time_text()
        if hasattr(self, "clock_label"):
            self.clock_label.text = current
        if hasattr(self, "broadcast_clock_label"):
            self.broadcast_clock_label.text = current

    def _start_clock(self) -> None:
        if self._clock_event is None:
            self._update_clock()
            self._clock_event = Clock.schedule_interval(self._update_clock, 1)

    def _stop_clock(self) -> None:
        if self._clock_event is not None:
            self._clock_event.cancel()
            self._clock_event = None


__all__ = [
    "MatchEntryScreen",
    "TURN_OPTIONS",
    "TURN_VALUE_TO_LABEL",
    "RESULT_OPTIONS",
    "RESULT_VALUE_TO_LABEL",
]
