import math
from datetime import datetime
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Optional

from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.anchorlayout import MDAnchorLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import (
    MDRaisedButton,
    MDFlatButton,
    MDIconButton,
    MDRectangleFlatButton,
    MDRectangleFlatIconButton,
)
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineListItem
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.core.window import Window
from kivy.clock import Clock
from kivymd.toast import toast
from kivymd.uix.dialog import MDDialog

from function.resources import get_text
from function.config import load_config, save_config, get_config_path
from function import DatabaseManager, DatabaseError, DuplicateEntryError
from function.logger import log_error

# 日本語フォント設定
_FONT_PATH = Path(__file__).resolve().parent / "resource" / "theme" / "font" / "mgenplus-1c-regular.ttf"
if _FONT_PATH.exists():
    LabelBase.register(DEFAULT_FONT, str(_FONT_PATH))


class _FallbackAppState:
    """Provide default attributes when no running MDApp is available."""

    def __init__(self):
        self.theme_cls = SimpleNamespace(primary_color=(0.2, 0.6, 0.86, 1))
        self.reset()

    def reset(self):
        self.config = load_config()
        self.ui_mode = self.config.get("ui", {}).get("mode", "normal")
        self.decks = []
        self.seasons = []
        self.match_records = []
        self.current_match_settings: Optional[dict[str, Any]] = None
        self.current_match_count = 0
        self.db: Optional[DatabaseManager] = None
        self.opponent_decks: list[str] = []
        self.default_window_size = Window.size
        self.migration_result: str = ""


_fallback_app_state = _FallbackAppState()


def get_app_state():
    """Return the running app instance or a fallback with default attributes."""

    app = MDApp.get_running_app()
    if app is None:
        return _fallback_app_state
    return app


def log_db_error(context: str, exc: Exception | None = None, **info) -> None:
    """Persist database error details to the log folder."""

    log_error(context, exc, **info)


def build_header(title, back_callback=None, top_callback=None):
    """アプリ画面上部のヘッダーを生成する共通ユーティリティ."""

    header = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(64),
        padding=(dp(12), dp(12), dp(12), dp(12)),
        spacing=dp(12),
    )

    action_box = MDBoxLayout(
        orientation="horizontal",
        spacing=dp(8),
        size_hint_x=None,
    )
    action_box.bind(minimum_width=action_box.setter("width"))

    button_style = {
        "size_hint": (None, None),
        "height": dp(40),
        "md_bg_color": (0.93, 0.96, 0.98, 1),
        "text_color": (0.18, 0.36, 0.58, 1),
        "line_color": (0.18, 0.36, 0.58, 1),
    }

    if top_callback is not None:
        top_button = MDRectangleFlatIconButton(
            text=get_text("common.return_to_top"),
            icon="home",
            on_press=lambda *_: top_callback(),
        )
        for key, value in button_style.items():
            setattr(top_button, key, value)
        action_box.add_widget(top_button)

    if back_callback is not None:
        back_button = MDRectangleFlatIconButton(
            text=get_text("common.back"),
            icon="arrow-left",
            on_press=lambda *_: back_callback(),
        )
        for key, value in button_style.items():
            setattr(back_button, key, value)
        action_box.add_widget(back_button)

    if action_box.children:
        header.add_widget(action_box)
        right_spacer = Widget(size_hint_x=None, width=action_box.width)

        def _sync_width(instance, value):
            right_spacer.width = value

        action_box.bind(width=_sync_width)
    else:
        placeholder_width = dp(48)
        header.add_widget(Widget(size_hint_x=None, width=placeholder_width))
        right_spacer = Widget(size_hint_x=None, width=placeholder_width)

    header_label = MDLabel(text=title, font_style="H5", halign="center")
    header_label.size_hint_x = 1
    header.add_widget(header_label)

    header.add_widget(right_spacer)

    return header


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


def _parse_schedule_datetime(date_text: str | None, time_text: str | None) -> Optional[datetime]:
    if not date_text:
        return None
    try:
        if time_text:
            return datetime.strptime(f"{date_text} {time_text}", "%Y-%m-%d %H:%M")
        return datetime.strptime(date_text, "%Y-%m-%d")
    except ValueError:
        return None


def _days_until(target: datetime) -> int:
    delta = target - datetime.now()
    if delta.total_seconds() <= 0:
        return 0
    return math.ceil(delta.total_seconds() / 86400)

class MenuScreen(MDScreen):
    """アプリケーションの初期画面."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.migration_dialog: MDDialog | None = None

        # 画面全体の配置を縦方向に整えるルートレイアウト
        root_layout = MDBoxLayout(orientation="vertical", spacing=0)

        # ヘッダーを追加し、アプリ名を常に表示
        root_layout.add_widget(build_header(get_text("menu.title")))

        # メインコンテンツはスクロール可能にし、長い情報でも表示が崩れないようにする
        scroll_view = ScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            padding=(dp(24), dp(24), dp(24), dp(32)),
            spacing=dp(24),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        # ヒーローカードとナビゲーション項目を順番に追加
        content.add_widget(self._build_hero_card())
        content.add_widget(self._build_navigation_grid())

        content.add_widget(
            MDLabel(
                text=get_text("common.version"),
                halign="center",
                theme_text_color="Hint",
                size_hint_y=None,
                height=dp(24),
            )
        )

        scroll_view.add_widget(content)
        root_layout.add_widget(scroll_view)
        self.add_widget(root_layout)

    def on_pre_enter(self):
        app = get_app_state()
        message = getattr(app, "migration_result", "")
        if message:
            Clock.schedule_once(lambda *_: self._show_migration_message(message), 0)
            app.migration_result = ""

    def _show_migration_message(self, message: str):
        if self.migration_dialog:
            self.migration_dialog.dismiss()
        self.migration_dialog = MDDialog(
            title=get_text("settings.db_migration_title"),
            text=message,
            buttons=[
                MDFlatButton(
                    text=get_text("common.close"),
                    on_release=lambda *_: self._dismiss_dialog(),
                )
            ],
        )
        self.migration_dialog.open()

    def _dismiss_dialog(self):
        if self.migration_dialog:
            self.migration_dialog.dismiss()
            self.migration_dialog = None

    def _build_hero_card(self):
        # アプリ紹介を行うカードレイアウト
        card = MDCard(
            orientation="vertical",
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(1, None),
            height=dp(220),
            md_bg_color=self.theme_cls.primary_color,
            radius=[24, 24, 24, 24],
        )

        card.add_widget(
            MDLabel(
                text=get_text("menu.hero_title"),
                font_style="H4",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
            )
        )
        card.add_widget(
            MDLabel(
                text=get_text("menu.hero_body"),
                theme_text_color="Custom",
                text_color=(1, 1, 1, 0.85),
            )
        )

        # メインアクションボタンを並べる行
        actions = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(48))
        actions.add_widget(
            MDRaisedButton(
                text=get_text("menu.primary_action"),
                on_press=lambda *_: self.change_screen("match_setup"),
            )
        )
        actions.add_widget(
            MDFlatButton(
                text=get_text("menu.secondary_action"),
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                on_press=lambda *_: self.change_screen("stats"),
            )
        )
        card.add_widget(actions)

        return card

    def _build_navigation_grid(self):
        # 主要機能へ移動するためのカード一覧を作成
        grid = MDGridLayout(
            cols=1,
            spacing=dp(16),
            size_hint_y=None,
            adaptive_height=True,
        )

        grid.add_widget(
            self._create_menu_option(
                icon="cards",
                title=get_text("menu.options.deck_register.title"),
                description=get_text("menu.options.deck_register.description"),
                screen_name="deck_register",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="calendar",
                title=get_text("menu.options.season_register.title"),
                description=get_text("menu.options.season_register.description"),
                screen_name="season_list",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="clipboard-text",
                title=get_text("menu.options.match_setup.title"),
                description=get_text("menu.options.match_setup.description"),
                screen_name="match_setup",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="chart-areaspline",
                title=get_text("menu.options.stats.title"),
                description=get_text("menu.options.stats.description"),
                screen_name="stats",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="cog",
                title=get_text("menu.options.settings.title"),
                description=get_text("menu.options.settings.description"),
                screen_name="settings",
            )
        )

        return grid

    def _create_menu_option(self, icon, title, description, screen_name):
        # メニューカード一枚分のレイアウトを生成
        card = MDCard(
            orientation="vertical",
            padding=(dp(20), dp(20), dp(20), dp(20)),
            size_hint=(1, None),
            height=dp(180),
            radius=[18, 18, 18, 18],
            elevation=2,
        )

        # アイコンとタイトルを横並びで配置
        header = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(36))
        header.add_widget(MDIcon(icon=icon, size_hint=(None, None), size=(dp(36), dp(36))))
        header.add_widget(
            MDLabel(
                text=title,
                font_style="H5",
                theme_text_color="Primary",
            )
        )
        card.add_widget(header)

        # 説明文を本文として追加
        card.add_widget(
            MDLabel(
                text=description,
                theme_text_color="Secondary",
            )
        )

        # 詳細画面へ遷移するボタン行
        button_row = MDBoxLayout(size_hint_y=None, height=dp(48), padding=(0, dp(12), 0, 0))
        button_row.add_widget(Widget())
        button_row.add_widget(
            MDRaisedButton(
                text=get_text("common.open"),
                on_press=lambda *_: self.change_screen(screen_name),
            )
        )
        card.add_widget(button_row)

        return card

    def change_screen(self, screen_name):
        # メニュー内から他画面へ遷移するヘルパー
        if self.manager:
            self.manager.current = screen_name

class BaseManagedScreen(MDScreen):
    def _create_scaffold(
        self,
        title: str,
        back_callback=None,
        top_callback=None,
        *,
        action_anchor_x: str = "center",
    ):
        root = MDBoxLayout(orientation="vertical")

        title_anchor = MDAnchorLayout(
            size_hint_y=1, anchor_x="center", anchor_y="center"
        )
        header = build_header(title, back_callback, top_callback)
        header.size_hint_y = None
        header.height = dp(64)
        header.size_hint_x = 0.95
        title_anchor.add_widget(header)

        content_anchor = MDAnchorLayout(
            size_hint_y=8, anchor_x="center", anchor_y="center"
        )
        action_anchor = MDAnchorLayout(
            size_hint_y=1, anchor_x=action_anchor_x, anchor_y="center"
        )

        root.add_widget(title_anchor)
        root.add_widget(content_anchor)
        root.add_widget(action_anchor)

        self.add_widget(root)
        return root, content_anchor, action_anchor

    def change_screen(self, screen_name):
        # 指定された画面名へ遷移する共通処理
        if self.manager:
            self.manager.current = screen_name

    def _sync_window_size(self, mode: str) -> None:
        """モードに応じてウィンドウサイズを調整する."""

        app = get_app_state()
        default_size = getattr(app, "default_window_size", Window.size)

        if mode == "broadcast":
            target_size = (1080, 280)
        else:
            target_size = default_size

        if tuple(Window.size) != tuple(target_size):
            Window.size = target_size


class DeckRegistrationScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # 入力欄の準備: デッキ名・説明・登録済み一覧
        self.name_field = MDTextField(
            hint_text=get_text("deck_registration.name_hint"),
            helper_text=get_text("common.required_helper"),
            helper_text_mode="on_focus",
        )
        self.description_field = MDTextField(
            hint_text=get_text("deck_registration.description_hint"),
            multiline=True,
            max_text_length=200,
        )
        # 登録済みデッキ表示用のコンテナ（スクロール対応）
        self.deck_empty_label = MDLabel(
            text=get_text("deck_registration.empty_message"),
            theme_text_color="Hint",
            size_hint_y=None,
            height=dp(24),
        )
        self.deck_list_container = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=(0, 0, 0, dp(8)),
            size_hint_y=None,
        )
        self.deck_list_container.bind(minimum_height=self.deck_list_container.setter("height"))
        self.deck_scroll = ScrollView(size_hint=(1, 1))
        self.deck_scroll.add_widget(self.deck_list_container)

        self.root_layout, content_anchor, action_anchor = self._create_scaffold(
            get_text("deck_registration.header_title"),
            lambda: self.change_screen("menu"),
            lambda: self.change_screen("menu"),
        )

        content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(0.95, 0.95),
        )
        content_box.add_widget(self.name_field)
        content_box.add_widget(self.description_field)
        content_box.add_widget(self.deck_empty_label)
        content_box.add_widget(self.deck_scroll)
        content_anchor.add_widget(content_box)

        register_button = MDRaisedButton(
            text=get_text("common.register"),
            on_press=lambda *_: self.register_deck(),
        )
        register_button.size_hint = (None, None)
        register_button.height = dp(48)
        register_button.width = dp(220)
        action_anchor.add_widget(register_button)

    def register_deck(self):
        # 入力値を取得し、空欄がないか確認
        name = self.name_field.text.strip()
        description = self.description_field.text.strip()

        if not name:
            toast(get_text("deck_registration.toast_missing_name"))
            return

        app = get_app_state()
        db = getattr(app, "db", None)

        if db is None:
            toast(get_text("common.db_error"))
            return

        try:
            db.add_deck(name, description)
        except DuplicateEntryError:
            toast(get_text("deck_registration.toast_duplicate"))
            return
        except DatabaseError as exc:
            log_db_error("Failed to add deck", exc, name=name)
            toast(get_text("common.db_error"))
            return

        app.decks = db.fetch_decks()
        toast(get_text("deck_registration.toast_registered"))
        self.name_field.text = ""
        self.description_field.text = ""
        self.update_deck_list()

    def on_pre_enter(self):
        # 画面表示前に最新の登録一覧を反映
        self.update_deck_list()

    def update_deck_list(self):
        # アプリ全体のデッキ情報を参照して表示を更新
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.decks = db.fetch_decks()
        self.deck_list_container.clear_widgets()

        if not app.decks:
            self.deck_empty_label.height = dp(24)
            self.deck_empty_label.opacity = 1
            self.deck_scroll.opacity = 0
            self.deck_scroll.size_hint_y = None
            self.deck_scroll.height = dp(0)
        else:
            self.deck_empty_label.height = dp(0)
            self.deck_empty_label.opacity = 0
            self.deck_scroll.opacity = 1
            self.deck_scroll.size_hint_y = 1
            for deck in app.decks:
                self.deck_list_container.add_widget(self._create_deck_card(deck))

    def _create_deck_card(self, deck: dict[str, str]):
        """登録済みデッキ 1 件分の情報をカード形式で描画する."""

        fallback_description = get_text("common.no_description")
        card = MDCard(
            orientation="horizontal",
            padding=(dp(16), dp(12), dp(12), dp(12)),
            size_hint=(1, None),
            height=dp(84),
            radius=[16, 16, 16, 16],
        )

        text_box = MDBoxLayout(orientation="vertical", spacing=dp(4))
        text_box.add_widget(
            MDLabel(text=deck["name"], font_style="Subtitle1", shorten=True)
        )
        text_box.add_widget(
            MDLabel(
                text=deck["description"] or fallback_description,
                theme_text_color="Secondary",
                shorten=True,
            )
        )

        card.add_widget(text_box)
        card.add_widget(Widget())

        delete_button = MDIconButton(
            icon="delete", on_release=lambda *_: self.delete_deck(deck["name"])
        )
        delete_button.theme_text_color = "Custom"
        delete_button.text_color = (0.86, 0.16, 0.16, 1)
        card.add_widget(delete_button)

        return card

    def delete_deck(self, name: str):
        """指定デッキを削除し一覧を再描画する."""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        try:
            db.delete_deck(name)
        except DatabaseError as exc:
            log_db_error("Failed to delete deck", exc, name=name)
            toast(get_text("common.db_error"))
            return

        app.decks = db.fetch_decks()
        toast(get_text("deck_registration.toast_deleted"))
        self.update_deck_list()


class SeasonListScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.season_empty_label = MDLabel(
            text=get_text("season_registration.empty_message"),
            theme_text_color="Hint",
            size_hint_y=None,
            height=dp(24),
        )
        self.season_list_container = MDBoxLayout(
            orientation="vertical",
            spacing=dp(8),
            padding=(0, 0, 0, dp(8)),
            size_hint_y=None,
        )
        self.season_list_container.bind(
            minimum_height=self.season_list_container.setter("height")
        )
        self.season_scroll = ScrollView(size_hint=(0.95, 0.95))
        self.season_scroll.add_widget(self.season_list_container)

        (
            self.root_layout,
            content_anchor,
            action_anchor,
        ) = self._create_scaffold(
            get_text("season_registration.list_header_title"),
            lambda: self.change_screen("menu"),
            lambda: self.change_screen("menu"),
            action_anchor_x="right",
        )

        content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(0.95, 0.95),
        )
        content_box.add_widget(self.season_empty_label)
        content_box.add_widget(self.season_scroll)
        content_anchor.add_widget(content_box)

        add_button = MDRaisedButton(
            text=get_text("season_registration.add_button"),
            on_press=lambda *_: self.change_screen("season_register"),
        )
        add_button.size_hint = (None, None)
        add_button.height = dp(48)
        add_button.width = dp(260)
        action_anchor.add_widget(add_button)

    def on_pre_enter(self):
        self.update_season_list()

    def update_season_list(self):
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.seasons = db.fetch_seasons()
        self.season_list_container.clear_widgets()

        if not app.seasons:
            self.season_empty_label.height = dp(24)
            self.season_empty_label.opacity = 1
            self.season_scroll.opacity = 0
            self.season_scroll.size_hint_y = None
            self.season_scroll.height = dp(0)
        else:
            self.season_empty_label.height = dp(0)
            self.season_empty_label.opacity = 0
            self.season_scroll.opacity = 1
            self.season_scroll.size_hint_y = 1
            self.season_scroll.height = 0
            for season in app.seasons:
                self.season_list_container.add_widget(
                    self._create_season_card(season)
                )

    def _create_season_card(self, season: dict[str, object]):
        card = MDCard(
            orientation="horizontal",
            padding=(dp(16), dp(12), dp(12), dp(12)),
            size_hint=(1, None),
            height=dp(72),
            radius=[16, 16, 16, 16],
        )
        card.spacing = dp(12)

        name_label = MDLabel(
            text=season["name"],
            font_style="Subtitle1",
            shorten=True,
        )
        name_label.size_hint_x = 0.55
        card.add_widget(name_label)

        remaining_label = MDLabel(
            text=self._get_remaining_text(season),
            theme_text_color="Secondary",
            halign="center",
            shorten=True,
        )
        remaining_label.size_hint_x = 0.35
        card.add_widget(remaining_label)

        delete_button = MDIconButton(
            icon="delete", on_release=lambda *_: self.delete_season(season["name"])
        )
        delete_button.theme_text_color = "Custom"
        delete_button.text_color = (0.86, 0.16, 0.16, 1)
        delete_button.size_hint = (None, None)
        delete_button.height = dp(48)
        card.add_widget(delete_button)

        return card

    def _get_remaining_text(self, season: dict[str, object]) -> str:
        end_date = season.get("end_date") or ""
        end_time = season.get("end_time") or ""
        end_dt = _parse_schedule_datetime(end_date, end_time)

        if not end_dt:
            return get_text("season_registration.schedule_no_end")

        if end_dt <= datetime.now():
            return get_text("season_registration.schedule_finished")

        days = _days_until(end_dt)
        return get_text("season_registration.schedule_ends_in").format(days=days)

    def delete_season(self, name: str):
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        try:
            db.delete_season(name)
        except DatabaseError as exc:
            log_db_error("Failed to delete season", exc, name=name)
            toast(get_text("common.db_error"))
            return

        app.seasons = db.fetch_seasons()
        toast(get_text("season_registration.toast_deleted"))
        self.update_season_list()


class SeasonRegistrationScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # シーズン名入力欄を作成
        self.name_field = MDTextField(
            hint_text=get_text("season_registration.name_hint"),
            helper_text=get_text("common.required_helper"),
            helper_text_mode="on_focus",
        )
        # シーズンの説明文入力欄を作成
        self.description_field = MDTextField(
            hint_text=get_text("season_registration.description_hint"),
            multiline=True,
            max_text_length=200,
        )
        self.start_date_field = MDTextField(
            hint_text=get_text("season_registration.start_date_hint"),
        )
        self.start_time_field = MDTextField(
            hint_text=get_text("season_registration.start_time_hint"),
        )
        self.end_date_field = MDTextField(
            hint_text=get_text("season_registration.end_date_hint"),
        )
        self.end_time_field = MDTextField(
            hint_text=get_text("season_registration.end_time_hint"),
        )
        (
            self.root_layout,
            content_anchor,
            action_anchor,
        ) = self._create_scaffold(
            get_text("season_registration.header_title"),
            lambda: self.change_screen("season_list"),
            lambda: self.change_screen("menu"),
        )

        content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(0.95, 0.95),
        )
        content_box.add_widget(self.name_field)
        content_box.add_widget(self.description_field)
        content_box.add_widget(
            MDLabel(
                text=get_text("season_registration.schedule_section_title"),
                theme_text_color="Secondary",
            )
        )

        schedule_box = MDBoxLayout(orientation="vertical", spacing=dp(12))

        start_row = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(72))
        for field in (self.start_date_field, self.start_time_field):
            field.size_hint = (1, None)
            field.height = dp(72)
            start_row.add_widget(field)
        schedule_box.add_widget(start_row)

        end_row = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(72))
        for field in (self.end_date_field, self.end_time_field):
            field.size_hint = (1, None)
            field.height = dp(72)
            end_row.add_widget(field)
        schedule_box.add_widget(end_row)

        content_box.add_widget(schedule_box)
        content_anchor.add_widget(content_box)

        actions = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(16),
            size_hint=(0.6, None),
            height=dp(48),
        )
        register_button = MDRaisedButton(
            text=get_text("common.register"),
            on_press=lambda *_: self.register_season(),
        )
        register_button.size_hint = (1, None)
        register_button.height = dp(48)
        back_button = MDFlatButton(
            text=get_text("season_registration.back_to_list"),
            on_press=lambda *_: self.change_screen("season_list"),
        )
        back_button.size_hint = (1, None)
        back_button.height = dp(48)
        actions.add_widget(back_button)
        actions.add_widget(register_button)
        action_anchor.add_widget(actions)
        self.reset_form()

    def register_season(self):
        # 入力内容を取得し、必須項目の確認を行う
        name = self.name_field.text.strip()
        description = self.description_field.text.strip()

        if not name:
            toast(get_text("season_registration.toast_missing_name"))
            return

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        start_date = self.start_date_field.text.strip() or None
        start_time = self.start_time_field.text.strip() or None
        end_date = self.end_date_field.text.strip() or None
        end_time = self.end_time_field.text.strip() or None

        try:
            db.add_season(
                name,
                description,
                start_date=start_date,
                start_time=start_time,
                end_date=end_date,
                end_time=end_time,
            )
        except DuplicateEntryError:
            toast(get_text("season_registration.toast_duplicate"))
            return
        except DatabaseError as exc:
            log_db_error("Failed to add season", exc, name=name)
            toast(get_text("common.db_error"))
            return

        app.seasons = db.fetch_seasons()
        toast(get_text("season_registration.toast_registered"))
        self.reset_form()
        self.change_screen("season_list")

    def reset_form(self):
        self.name_field.text = ""
        self.description_field.text = ""
        self.start_date_field.text = ""
        self.start_time_field.text = ""
        self.end_date_field.text = ""
        self.end_time_field.text = ""


class MatchSetupScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_deck = None
        self.deck_menu = None

        # 対戦カウントとデッキ選択の入力部品を用意
        self.match_count_field = MDTextField(
            hint_text=get_text("match_setup.count_hint"),
            input_filter="int",
            text="0",
        )
        self.deck_button = MDRaisedButton(
            text=get_text("match_setup.deck_button_default"),
            on_press=lambda *_: self.open_deck_menu(),
        )

        (
            self.normal_root,
            content_anchor,
            self.normal_action_anchor,
        ) = self._create_scaffold(
            get_text("match_setup.header_title"),
            lambda: self.change_screen("menu"),
            lambda: self.change_screen("menu"),
        )

        self.count_label = MDLabel(
            text=get_text("match_setup.count_label"),
            font_style="Subtitle1",
        )
        self.deck_label = MDLabel(
            text=get_text("match_setup.deck_label"),
            font_style="Subtitle1",
        )

        self.match_count_field.size_hint = (1, None)
        self.match_count_field.height = dp(72)
        self.deck_button.size_hint = (1, None)
        self.deck_button.height = dp(48)

        self.normal_content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(0.95, 0.95),
        )
        self.normal_content_box.add_widget(self.count_label)
        self.normal_content_box.add_widget(self.match_count_field)
        self.normal_content_box.add_widget(self.deck_label)
        self.normal_content_box.add_widget(self.deck_button)
        content_anchor.add_widget(self.normal_content_box)

        self.start_button = MDRaisedButton(
            text=get_text("match_setup.start_button"),
            on_press=lambda *_: self.start_entry(),
        )
        self.start_button.size_hint = (None, None)
        self.start_button.height = dp(48)
        self.start_button.width = dp(220)
        self.normal_action_anchor.add_widget(self.start_button)

        self.broadcast_layout = self._build_broadcast_layout()

    def on_pre_enter(self):
        # 画面に入るたびに選択状態をリセット
        self.selected_deck = None
        self.deck_button.text = get_text("match_setup.deck_button_default")

        app = get_app_state()
        mode = getattr(app, "ui_mode", "normal")
        self._apply_mode_layout(mode)
        self._sync_window_size(mode)

    def open_deck_menu(self):
        # 登録済みデッキから選択肢を生成しドロップダウンで表示
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.decks = db.fetch_decks()
        if not app.decks:
            toast(get_text("match_setup.toast_no_decks"))
            return

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": deck["name"],
                "on_release": lambda name=deck["name"]: self.set_selected_deck(name),
            }
            for deck in app.decks
        ]

        if self.deck_menu:
            # 既存のメニューがある場合は閉じてから新しいものを開く
            self.deck_menu.dismiss()

        self.deck_menu = MDDropdownMenu(caller=self.deck_button, items=menu_items, width_mult=4)
        self.deck_menu.open()

    def set_selected_deck(self, name):
        self.selected_deck = name
        self.deck_button.text = get_text("match_setup.selected_deck_label").format(
            deck_name=name
        )
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            next_no = db.get_next_match_number(name)
            self.match_count_field.text = str(next_no)
        if self.deck_menu:
            self.deck_menu.dismiss()

    def start_entry(self):
        if not self.selected_deck:
            toast(get_text("match_setup.toast_select_deck"))
            return

        # 入力値が整数として妥当かチェック
        try:
            initial_count = int(self.match_count_field.text or 0)
        except ValueError:
            toast(get_text("match_setup.toast_invalid_count"))
            return

        # 設定値をアプリ全体の状態として保持
        app = get_app_state()
        app.current_match_settings = {
            "count": initial_count,
            "deck_name": self.selected_deck,
        }
        app.current_match_count = initial_count

        toast(get_text("match_setup.toast_start"))
        self.change_screen("match_entry")

    def _build_broadcast_layout(self) -> MDBoxLayout:
        layout = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(12),
            padding=(dp(12), dp(12), dp(12), dp(12)),
        )

        nav_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=1,
        )
        for icon, callback in (
            ("home", lambda *_: self.change_screen("menu")),
            ("arrow-left", lambda *_: self.change_screen("menu")),
        ):
            button = MDIconButton(icon=icon, on_release=callback)
            button.theme_text_color = "Custom"
            button.text_color = (0.18, 0.36, 0.58, 1)
            button.size_hint = (None, None)
            button.height = dp(48)
            button.width = dp(48)
            nav_section.add_widget(button)
        layout.add_widget(nav_section)

        self.broadcast_form_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=5,
            padding=(dp(12), dp(12), dp(12), dp(12)),
        )
        layout.add_widget(self.broadcast_form_section)

        self.broadcast_actions_section = MDBoxLayout(
            orientation="vertical",
            spacing=dp(12),
            size_hint_x=2,
        )
        layout.add_widget(self.broadcast_actions_section)

        return layout

    @staticmethod
    def _remove_from_parent(widget):
        parent = widget.parent
        if parent is not None:
            parent.remove_widget(widget)

    def _apply_mode_layout(self, mode: str) -> None:
        if mode == "broadcast":
            self._show_broadcast_layout()
        else:
            self._show_normal_layout()

    def _show_broadcast_layout(self) -> None:
        if self.normal_root.parent:
            self.remove_widget(self.normal_root)
        if not self.broadcast_layout.parent:
            self.add_widget(self.broadcast_layout)

        self.broadcast_form_section.clear_widgets()
        for widget in (
            self.count_label,
            self.match_count_field,
            self.deck_label,
            self.deck_button,
        ):
            self._remove_from_parent(widget)
            self.broadcast_form_section.add_widget(widget)

        self.broadcast_actions_section.clear_widgets()
        self._remove_from_parent(self.start_button)
        self.start_button.size_hint = (1, None)
        self.start_button.width = dp(180)
        self.broadcast_actions_section.add_widget(self.start_button)

    def _show_normal_layout(self) -> None:
        if self.broadcast_layout.parent:
            self.remove_widget(self.broadcast_layout)
        if not self.normal_root.parent:
            self.add_widget(self.normal_root)

        for widget in (
            self.count_label,
            self.match_count_field,
            self.deck_label,
            self.deck_button,
        ):
            self._remove_from_parent(widget)
            if widget not in self.normal_content_box.children:
                self.normal_content_box.add_widget(widget)

        self._remove_from_parent(self.start_button)
        self.start_button.size_hint = (None, None)
        self.start_button.width = dp(220)
        if self.start_button not in self.normal_action_anchor.children:
            self.normal_action_anchor.add_widget(self.start_button)

    def on_leave(self):
        app = get_app_state()
        default_size = getattr(app, "default_window_size", None)
        if default_size:
            Window.size = default_size



class MatchEntryScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.turn_choice: Optional[bool] = None
        self.result_choice: Optional[int] = None
        self.turn_buttons: list[MDRectangleFlatButton] = []
        self.result_buttons: list[MDRectangleFlatButton] = []
        self.last_record_data = None
        self._clock_event = None

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

        self.match_info_label = MDLabel(
            text="",
            halign="center",
            font_style="Subtitle1",
        )

        self.status_label = MDLabel(
            text=get_text("match_entry.status_default"),
            halign="center",
            font_style="H5",
        )

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
        self.result_prompt_label = MDLabel(
            text=get_text("match_entry.result_prompt"),
            theme_text_color="Secondary",
        )

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
            spacing=dp(4),
            size_hint=(1, None),
            height=dp(96),
        )
        time_box.bind(minimum_height=time_box.setter("height"))
        self.broadcast_clock_label = MDLabel(
            text=self._get_current_time_text(),
            halign="center",
            font_style="H5",
        )
        self.broadcast_match_info_label = MDLabel(
            text="",
            halign="center",
            font_style="Subtitle1",
        )
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
        if mode == "broadcast":
            self._show_broadcast_layout()
        else:
            self._show_normal_layout()

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


class StatsScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_deck = None
        self.deck_menu = None

        self.stats_label = MDLabel(
            text=get_text("stats.no_data"),
            theme_text_color="Secondary",
        )

        self.filter_button = MDRaisedButton(
            text=get_text("stats.filter_button"),
            on_press=lambda *_: self.open_deck_menu(),
        )
        self.filter_button.size_hint = (1, None)
        self.filter_button.height = dp(48)

        (
            self.root_layout,
            content_anchor,
            action_anchor,
        ) = self._create_scaffold(
            get_text("stats.header_title"),
            lambda: self.change_screen("menu"),
            lambda: self.change_screen("menu"),
        )

        content_box = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint=(0.95, 0.95),
        )
        content_box.add_widget(self.filter_button)
        content_box.add_widget(self.stats_label)
        content_anchor.add_widget(content_box)

        clear_button = MDFlatButton(
            text=get_text("common.clear_filter"),
            on_press=lambda *_: self.clear_filter(),
        )
        clear_button.size_hint = (None, None)
        clear_button.height = dp(48)
        clear_button.width = dp(200)
        action_anchor.add_widget(clear_button)

    def on_pre_enter(self):
        # 画面表示の度に最新の統計を再計算
        self.update_stats()

    def open_deck_menu(self):
        # 登録済みデッキから絞り込み候補を作成
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is not None:
            app.decks = db.fetch_decks()
        if not app.decks:
            toast(get_text("stats.toast_no_decks"))
            return

        menu_items = [
            {
                "viewclass": "OneLineListItem",
                "text": deck["name"],
                "on_release": lambda name=deck["name"]: self.set_deck_filter(name),
            }
            for deck in app.decks
        ]

        if self.deck_menu:
            # 古いメニューを閉じてから新しいメニューを開く
            self.deck_menu.dismiss()

        self.deck_menu = MDDropdownMenu(caller=self.filter_button, items=menu_items, width_mult=4)
        self.deck_menu.open()

    def set_deck_filter(self, name):
        # 選択されたデッキ名で絞り込み条件を設定
        self.selected_deck = name
        if self.deck_menu:
            self.deck_menu.dismiss()
        self.filter_button.text = get_text("stats.filter_label").format(deck_name=name)
        self.update_stats()

    def clear_filter(self):
        # 条件を解除して全データを対象に戻す
        self.selected_deck = None
        self.filter_button.text = get_text("stats.filter_button")
        self.update_stats()

    def update_stats(self):
        # 試合記録から統計情報を計算し、表示内容を組み立てる
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            self.stats_label.text = get_text("common.db_error")
            return

        records = db.fetch_matches(self.selected_deck)

        if not records:
            # 条件に合致するデータが無い場合のメッセージ
            if self.selected_deck:
                self.stats_label.text = get_text("stats.no_data_for_deck").format(
                    deck_name=self.selected_deck
                )
            else:
                self.stats_label.text = get_text("stats.no_data")
            return

        total = len(records)
        wins = sum(1 for r in records if int(r["result"]) > 0)
        draws = sum(1 for r in records if int(r["result"]) == 0)
        losses = total - wins - draws
        win_rate = (wins / total) * 100

        # 集計結果を見やすい文字列にまとめてラベルへ反映
        header = get_text("stats.filter_label").format(
            deck_name=self.selected_deck or get_text("stats.filter_all")
        )
        self.stats_label.text = get_text("stats.summary_template").format(
            header=header,
            total=total,
            wins=wins,
            draws=draws,
            losses=losses,
            win_rate=win_rate,
        )


class SettingsScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.confirm_dialog: MDDialog | None = None
        self.mode_buttons: dict[str, MDRectangleFlatIconButton] = {}
        self.backup_info_label: MDLabel | None = None

        (
            self.root_layout,
            content_anchor,
            action_anchor,
        ) = self._create_scaffold(
            get_text("settings.header_title"),
            lambda: self.change_screen("menu"),
            lambda: self.change_screen("menu"),
        )

        self.settings_scroll = ScrollView(size_hint=(0.95, 0.95))
        self.settings_container = MDBoxLayout(
            orientation="vertical",
            spacing=dp(16),
            padding=(dp(24), dp(24), dp(24), dp(24)),
            size_hint_y=None,
        )
        self.settings_container.bind(
            minimum_height=self.settings_container.setter("height")
        )
        self.settings_scroll.add_widget(self.settings_container)
        self.settings_container.add_widget(self._build_ui_section())
        self.settings_container.add_widget(self._build_database_section())
        content_anchor.add_widget(self.settings_scroll)

        exit_button = MDRaisedButton(
            text=get_text("common.exit"),
            on_press=lambda *_: self.exit_app(),
        )
        exit_button.size_hint = (None, None)
        exit_button.height = dp(48)
        exit_button.width = dp(200)
        action_anchor.add_widget(exit_button)

    def on_pre_enter(self):
        app = get_app_state()
        mode = getattr(app, "ui_mode", "normal")
        self._update_mode_buttons(mode)
        self._update_backup_label()

    def _build_database_section(self):
        card = MDCard(
            orientation="vertical",
            padding=(dp(16), dp(16), dp(16), dp(16)),
            size_hint=(1, None),
            radius=[16, 16, 16, 16],
        )
        card.spacing = dp(12)
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            MDLabel(
                text=get_text("settings.db_section_title"),
                font_style="Subtitle1",
            )
        )
        card.add_widget(
            MDLabel(
                text=get_text("settings.backup_description"),
                theme_text_color="Secondary",
            )
        )
        self.backup_info_label = MDLabel(
            text="",
            theme_text_color="Hint",
        )
        card.add_widget(self.backup_info_label)
        backup_button = MDRaisedButton(
            text=get_text("settings.backup_button"),
            on_press=lambda *_: self.create_backup(),
        )
        backup_button.size_hint = (1, None)
        backup_button.height = dp(48)
        card.add_widget(backup_button)
        card.add_widget(
            MDLabel(
                text=get_text("settings.db_init_description"),
                theme_text_color="Secondary",
            )
        )
        init_button = MDRaisedButton(
            text=get_text("settings.db_init_button"),
            on_press=lambda *_: self.open_db_init_dialog(),
        )
        init_button.size_hint = (1, None)
        init_button.height = dp(48)
        card.add_widget(init_button)
        return card

    def _build_ui_section(self):
        card = MDCard(
            orientation="vertical",
            padding=(dp(16), dp(16), dp(16), dp(16)),
            size_hint=(1, None),
            radius=[16, 16, 16, 16],
        )
        card.spacing = dp(12)
        card.bind(minimum_height=card.setter("height"))
        card.add_widget(
            MDLabel(
                text=get_text("settings.ui_section_title"),
                font_style="Subtitle1",
            )
        )
        card.add_widget(
            MDLabel(
                text=get_text("settings.ui_mode_description"),
                theme_text_color="Secondary",
            )
        )

        button_row = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(48))
        modes = [
            ("normal", "settings.mode_normal", "monitor"),
            ("broadcast", "settings.mode_broadcast", "cast"),
        ]

        for mode_value, text_key, icon in modes:
            button = MDRectangleFlatIconButton(
                text=get_text(text_key),
                icon=icon,
            )
            button.size_hint = (1, None)
            button.height = dp(48)
            self.mode_buttons[mode_value] = button
            button_row.add_widget(button)

            def make_callback(value: str):
                return lambda *_: self._set_ui_mode(value)

            button.bind(on_press=make_callback(mode_value))

        card.add_widget(button_row)
        return card

    def _set_ui_mode(self, mode: str) -> None:
        app = get_app_state()
        app.ui_mode = mode
        if getattr(app, "config", None) is None:
            app.config = load_config()
        app.config.setdefault("ui", {})["mode"] = mode
        save_config(app.config)
        _fallback_app_state.ui_mode = mode
        _fallback_app_state.config = dict(app.config)
        self._update_mode_buttons(mode)
        toast(get_text("settings.mode_updated"))

    def _update_mode_buttons(self, selected: str) -> None:
        for mode, button in self.mode_buttons.items():
            if mode == selected:
                button.md_bg_color = (0.18, 0.36, 0.58, 1)
                button.text_color = (1, 1, 1, 1)
                button.line_color = (0.18, 0.36, 0.58, 1)
            else:
                button.md_bg_color = (1, 1, 1, 1)
                button.text_color = (0.18, 0.36, 0.58, 1)
                button.line_color = (0.18, 0.36, 0.58, 1)

    def _update_backup_label(self) -> None:
        if not self.backup_info_label:
            return
        app = get_app_state()
        config = getattr(app, "config", None) or load_config()
        last_backup = config.get("database", {}).get("last_backup")
        if last_backup:
            self.backup_info_label.text = get_text("settings.last_backup").format(
                path=last_backup
            )
        else:
            self.backup_info_label.text = get_text("settings.no_backup")

    def create_backup(self) -> None:
        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        try:
            backup_path = db.export_backup()
        except Exception:  # pragma: no cover - defensive
            toast(get_text("settings.backup_failure"))
            return

        if getattr(app, "config", None) is None:
            app.config = load_config()
        app.config.setdefault("database", {})["last_backup"] = str(backup_path)
        save_config(app.config)
        _fallback_app_state.config = dict(app.config)
        self._update_backup_label()
        toast(get_text("settings.backup_success"))

    def open_db_init_dialog(self):
        if self.confirm_dialog:
            self.confirm_dialog.dismiss()
        self.confirm_dialog = MDDialog(
            title=get_text("settings.db_init_button"),
            text=get_text("settings.db_init_confirm"),
            buttons=[
                MDFlatButton(
                    text=get_text("common.cancel"),
                    on_release=self._dismiss_dialog,
                ),
                MDRaisedButton(
                    text=get_text("common.execute"),
                    on_release=self._perform_db_initialization,
                ),
            ],
        )
        self.confirm_dialog.open()

    def _dismiss_dialog(self, *_):
        if self.confirm_dialog:
            self.confirm_dialog.dismiss()
            self.confirm_dialog = None

    def _perform_db_initialization(self, *_):
        self._dismiss_dialog()

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        try:
            db.initialize_database()
            app.decks = db.fetch_decks()
            app.seasons = db.fetch_seasons()
            app.match_records = []
            app.current_match_settings = None
            app.current_match_count = 0
            app.opponent_decks = []
            _fallback_app_state.db = db
            _fallback_app_state.decks = []
            _fallback_app_state.seasons = []
            _fallback_app_state.match_records = []
            _fallback_app_state.current_match_settings = None
            _fallback_app_state.current_match_count = 0
            _fallback_app_state.opponent_decks = []
        except Exception:  # pragma: no cover - defensive
            toast(get_text("settings.db_init_failure"))
            return

        toast(get_text("settings.db_init_success"))

    def exit_app(self):
        # アプリを終了しウィンドウを閉じる
        self._dismiss_dialog()
        app = MDApp.get_running_app()
        if app:
            app.stop()
        Window.close()

class DeckAnalyzerApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "BlueGray"
        self.config = load_config()
        self.ui_mode = self.config.get("ui", {}).get("mode", "normal")
        self.default_window_size = Window.size

        self.db = DatabaseManager()
        self.db.ensure_database()

        expected_version = self.config.get("database", {}).get(
            "expected_version", DatabaseManager.CURRENT_SCHEMA_VERSION
        )
        current_version = self.db.get_schema_version()
        if current_version != expected_version:
            self.migration_result = self._handle_version_mismatch(
                current_version, expected_version
            )
        else:
            self.migration_result = ""

        self.db.set_schema_version(expected_version)

        self.decks = self.db.fetch_decks()
        self.seasons = self.db.fetch_seasons()
        self.match_records = self.db.fetch_matches()
        self.opponent_decks = self.db.fetch_opponent_decks()
        self.current_match_settings = None
        self.current_match_count = 0

        _fallback_app_state.reset()
        _fallback_app_state.theme_cls.primary_color = self.theme_cls.primary_color
        _fallback_app_state.db = self.db
        _fallback_app_state.decks = list(self.decks)
        _fallback_app_state.seasons = list(self.seasons)
        _fallback_app_state.match_records = list(self.match_records)
        _fallback_app_state.opponent_decks = list(self.opponent_decks)
        _fallback_app_state.config = dict(self.config)
        _fallback_app_state.ui_mode = self.ui_mode
        _fallback_app_state.default_window_size = self.default_window_size
        _fallback_app_state.migration_result = self.migration_result

        sm = MDScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(DeckRegistrationScreen(name="deck_register"))
        sm.add_widget(SeasonListScreen(name="season_list"))
        sm.add_widget(SeasonRegistrationScreen(name="season_register"))
        sm.add_widget(MatchSetupScreen(name="match_setup"))
        sm.add_widget(MatchEntryScreen(name="match_entry"))
        sm.add_widget(StatsScreen(name="stats"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm

    def _handle_version_mismatch(self, current_version: int, expected_version: int) -> str:
        lines = [
            get_text("settings.db_migration_detected").format(
                current=current_version, expected=expected_version
            )
        ]

        try:
            backup_path = self.db.export_backup()
            lines.append(
                get_text("settings.db_migration_backup").format(path=str(backup_path))
            )
            self.config.setdefault("database", {})["last_backup"] = str(backup_path)
            save_config(self.config)

            self.db.initialize_database()
            self.db.set_schema_version(expected_version)

            try:
                restored = self.db.import_backup(backup_path)
            except DatabaseError as exc:
                log_db_error(
                    "Failed to restore database during migration", exc, backup=str(backup_path)
                )
                lines.append(
                    get_text("settings.db_migration_restore_failed").format(error=str(exc))
                )
                return "\n".join(
                    [get_text("settings.db_migration_failure").format(error=str(exc))]
                    + lines
                )
            else:
                lines.append(
                    get_text("settings.db_migration_restore_success").format(
                        decks=restored.get("decks", 0),
                        seasons=restored.get("seasons", 0),
                        matches=restored.get("matches", 0),
                    )
                )

            return "\n".join([get_text("settings.db_migration_success")] + lines)
        except Exception as exc:  # pragma: no cover - defensive
            return "\n".join(
                [
                    get_text("settings.db_migration_failure").format(error=str(exc)),
                    *lines,
                ]
            )

if __name__ == '__main__':
    DeckAnalyzerApp().run()
