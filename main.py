from types import SimpleNamespace
from typing import Any, Optional

from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
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
from kivymd.toast import toast
from kivymd.uix.dialog import MDDialog

from function.resources import get_text
from function import DatabaseManager, DatabaseError, DuplicateEntryError

# 日本語フォント設定
LabelBase.register(DEFAULT_FONT, r'resource\\theme\\font\\mgenplus-1c-regular.ttf')


class _FallbackAppState:
    """Provide default attributes when no running MDApp is available."""

    def __init__(self):
        self.theme_cls = SimpleNamespace(primary_color=(0.2, 0.6, 0.86, 1))
        self.reset()

    def reset(self):
        self.decks = []
        self.seasons = []
        self.match_records = []
        self.current_match_settings: Optional[dict[str, Any]] = None
        self.current_match_count = 0
        self.db: Optional[DatabaseManager] = None
        self.opponent_decks: list[str] = []


_fallback_app_state = _FallbackAppState()


def get_app_state():
    """Return the running app instance or a fallback with default attributes."""

    app = MDApp.get_running_app()
    if app is None:
        return _fallback_app_state
    return app


def build_header(title, back_callback=None):
    """アプリ画面上部のヘッダーを生成する共通ユーティリティ."""

    # 画面上部に固定配置されるヘッダーレイアウト。
    # 戻るボタン/タイトル/余白の 3 要素を横並びにし、
    # どの画面でも UI 一貫性を保つようにしている。
    header = MDBoxLayout(
        orientation="horizontal",
        size_hint_y=None,
        height=dp(64),
        padding=(dp(12), dp(12), dp(12), dp(12)),
        spacing=dp(12),
    )

    if back_callback is not None:
        # 左上に常に表示される戻るボタン。視認性向上のため背景色とアイコンを付与。
        back_button = MDRectangleFlatIconButton(
            text=get_text("common.back"),
            icon="arrow-left",
            on_press=lambda *_: back_callback(),
        )
        back_button.size_hint = (None, None)
        back_button.height = dp(40)
        back_button.md_bg_color = (0.93, 0.96, 0.98, 1)
        back_button.text_color = (0.18, 0.36, 0.58, 1)
        back_button.line_color = (0.18, 0.36, 0.58, 1)
        header.add_widget(back_button)
    else:
        # 戻るボタンなしでもタイトルが中央に来るようダミー領域を確保。
        header.add_widget(Widget(size_hint_x=None, width=dp(48)))

    header_label = MDLabel(text=title, font_style="H5", halign="center")
    header_label.size_hint_x = 1
    header.add_widget(header_label)

    # タイトルを正確に中央揃えにするため末尾にも余白を確保。
    header.add_widget(Widget(size_hint_x=None, width=dp(48)))

    return header

class MenuScreen(MDScreen):
    """アプリケーションの初期画面."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

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
                screen_name="season_register",
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
    def change_screen(self, screen_name):
        # 指定された画面名へ遷移する共通処理
        if self.manager:
            self.manager.current = screen_name


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

        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))

        # 画面タイトルと戻るボタンを持つヘッダー
        layout.add_widget(
            build_header(
                get_text("deck_registration.header_title"),
                lambda: self.change_screen("menu"),
            )
        )

        # 入力フォームとアクションボタンを順に配置
        layout.add_widget(self.name_field)
        layout.add_widget(self.description_field)
        layout.add_widget(
            MDRaisedButton(
                text=get_text("common.register"),
                on_press=lambda *_: self.register_deck(),
            )
        )
        layout.add_widget(self.deck_empty_label)
        layout.add_widget(self.deck_scroll)

        # メニュー画面へ戻るためのボタン
        back_button = MDFlatButton(
            text=get_text("common.return_to_top"),
            on_press=lambda *_: self.change_screen("menu"),
        )
        back_button.size_hint_y = None
        back_button.height = dp(48)
        layout.add_widget(back_button)

        self.add_widget(layout)

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
        except DatabaseError:
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
        except DatabaseError:
            toast(get_text("common.db_error"))
            return

        app.decks = db.fetch_decks()
        toast(get_text("deck_registration.toast_deleted"))
        self.update_deck_list()


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
        # 登録済みシーズンをまとめて表示するラベル
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
        self.season_list_container.bind(minimum_height=self.season_list_container.setter("height"))
        self.season_scroll = ScrollView(size_hint=(1, 1))
        self.season_scroll.add_widget(self.season_list_container)

        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        layout.add_widget(
            build_header(
                get_text("season_registration.header_title"),
                lambda: self.change_screen("menu"),
            )
        )
        layout.add_widget(self.name_field)
        layout.add_widget(self.description_field)
        layout.add_widget(
            MDRaisedButton(
                text=get_text("common.register"),
                on_press=lambda *_: self.register_season(),
            )
        )
        layout.add_widget(self.season_empty_label)
        layout.add_widget(self.season_scroll)
        back_button = MDFlatButton(
            text=get_text("common.return_to_top"),
            on_press=lambda *_: self.change_screen("menu"),
        )
        back_button.size_hint_y = None
        back_button.height = dp(48)
        layout.add_widget(back_button)

        self.add_widget(layout)

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

        try:
            db.add_season(name, description)
        except DuplicateEntryError:
            toast(get_text("season_registration.toast_duplicate"))
            return
        except DatabaseError:
            toast(get_text("common.db_error"))
            return

        app.seasons = db.fetch_seasons()
        toast(get_text("season_registration.toast_registered"))
        self.name_field.text = ""
        self.description_field.text = ""
        self.update_season_list()

    def on_pre_enter(self):
        # 表示直前に登録リストを最新状態へ
        self.update_season_list()

    def update_season_list(self):
        # 保持しているシーズン情報を整形し、利用者へ提示
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
            for season in app.seasons:
                self.season_list_container.add_widget(self._create_season_card(season))

    def _create_season_card(self, season: dict[str, str]):
        """シーズン情報 1 件を表示するカードを生成する."""

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
            MDLabel(text=season["name"], font_style="Subtitle1", shorten=True)
        )
        text_box.add_widget(
            MDLabel(
                text=season["description"] or fallback_description,
                theme_text_color="Secondary",
                shorten=True,
            )
        )

        card.add_widget(text_box)
        card.add_widget(Widget())

        delete_button = MDIconButton(
            icon="delete", on_release=lambda *_: self.delete_season(season["name"])
        )
        delete_button.theme_text_color = "Custom"
        delete_button.text_color = (0.86, 0.16, 0.16, 1)
        card.add_widget(delete_button)

        return card

    def delete_season(self, name: str):
        """指定シーズンを削除し、一覧を更新する."""

        app = get_app_state()
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        try:
            db.delete_season(name)
        except DatabaseError:
            toast(get_text("common.db_error"))
            return

        app.seasons = db.fetch_seasons()
        toast(get_text("season_registration.toast_deleted"))
        self.update_season_list()


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

        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        layout.add_widget(
            build_header(
                get_text("match_setup.header_title"),
                lambda: self.change_screen("menu"),
            )
        )
        # ラベルを追加し、入力項目の意味を明確にする
        layout.add_widget(
            MDLabel(
                text=get_text("match_setup.count_label"),
                font_style="Subtitle1",
                size_hint_y=None,
                height=dp(28),
            )
        )
        layout.add_widget(self.match_count_field)
        layout.add_widget(
            MDLabel(
                text=get_text("match_setup.deck_label"),
                font_style="Subtitle1",
                size_hint_y=None,
                height=dp(28),
            )
        )
        layout.add_widget(self.deck_button)
        layout.add_widget(
            MDRaisedButton(
                text=get_text("match_setup.start_button"),
                on_press=lambda *_: self.start_entry(),
            )
        )
        layout.add_widget(
            MDFlatButton(
                text=get_text("common.return_to_top"),
                on_press=lambda *_: self.change_screen("menu"),
            )
        )

        self.add_widget(layout)

    def on_pre_enter(self):
        # 画面に入るたびに選択状態をリセット
        self.selected_deck = None
        self.deck_button.text = get_text("match_setup.deck_button_default")

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


class MatchEntryScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.turn_choice = None
        self.result_choice = None
        self.turn_buttons = []
        self.result_buttons = []
        self.last_record_data = None

        header = build_header(
            get_text("match_entry.header_title"),
            lambda: self.change_screen("match_setup"),
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
        self.opponent_menu = None
        self.keyword_field = MDTextField(
            hint_text=get_text("match_entry.keyword_hint"),
            multiline=True,
        )

        root_layout = MDBoxLayout(orientation="vertical")
        root_layout.add_widget(header)

        scroll_view = ScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            padding=(dp(24), dp(24), dp(24), dp(24)),
            spacing=dp(16),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(self.status_label)
        content.add_widget(self._build_last_record_card())
        content.add_widget(
            MDLabel(
                text=get_text("match_entry.turn_prompt"),
                theme_text_color="Secondary",
            )
        )
        content.add_widget(
            self._build_toggle_row(
                get_text("match_entry.turn_options"),
                self.set_turn_choice,
                "turn_buttons",
            )
        )
        # 対戦相手デッキ名の入力欄とプルダウンボタンを横並びに配置
        opponent_row = MDBoxLayout(
            orientation="horizontal",
            spacing=dp(8),
            size_hint_y=None,
            height=dp(72),
        )
        self.opponent_field.size_hint_y = None
        self.opponent_field.height = dp(72)
        opponent_row.add_widget(self.opponent_field)
        self.opponent_menu_button.size_hint = (None, None)
        self.opponent_menu_button.height = dp(48)
        opponent_row.add_widget(self.opponent_menu_button)
        content.add_widget(opponent_row)
        content.add_widget(self.keyword_field)
        content.add_widget(
            MDLabel(
                text=get_text("match_entry.result_prompt"),
                theme_text_color="Secondary",
            )
        )
        content.add_widget(
            self._build_toggle_row(
                get_text("match_entry.result_options"),
                self.set_result_choice,
                "result_buttons",
            )
        )

        # 下部操作ボタンは横一列にまとめて操作感を統一
        quick_actions = MDBoxLayout(
            spacing=dp(12), size_hint_y=None, height=dp(48)
        )
        clear_button = MDFlatButton(
            text=get_text("match_entry.clear_button"),
            on_press=lambda *_: self.reset_inputs(focus_opponent=True),
        )
        clear_button.size_hint = (1, None)
        clear_button.height = dp(48)

        record_button = MDRaisedButton(
            text=get_text("match_entry.record_button"),
            on_press=lambda *_: self.submit_match(),
        )
        record_button.size_hint = (1, None)
        record_button.height = dp(48)

        back_button = MDFlatButton(
            text=get_text("match_entry.back_button"),
            on_press=lambda *_: self.change_screen("match_setup"),
        )
        back_button.size_hint = (1, None)
        back_button.height = dp(48)

        quick_actions.add_widget(clear_button)
        quick_actions.add_widget(record_button)
        quick_actions.add_widget(back_button)
        content.add_widget(quick_actions)

        scroll_view.add_widget(content)
        root_layout.add_widget(scroll_view)

        self.add_widget(root_layout)

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
        keywords_text = ", ".join(keywords) if keywords else get_text("match_entry.last_record_no_keywords")
        opponent_text = last_record.get("opponent_deck") or get_text("match_entry.last_record_no_opponent")
        self.last_record_label.text = get_text("match_entry.last_record_template").format(
            match_no=last_record.get("match_no"),
            turn=last_record.get("turn"),
            result=last_record.get("result"),
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

    def _build_toggle_row(self, options, callback, attr_name):
        """指定した選択肢をトグル可能なボタン行として構築する."""

        row = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(48))
        buttons = []

        app = get_app_state()
        primary_color = getattr(app.theme_cls, "primary_color", (0.2, 0.6, 0.86, 1))
        neutral_line = (0.7, 0.7, 0.7, 1)

        for option in options:
            button = MDRectangleFlatButton(text=option)
            button.size_hint = (1, None)
            button.height = dp(48)
            button.md_bg_color = (1, 1, 1, 1)
            button.text_color = primary_color
            button.line_color = neutral_line

            def make_callback(value):
                return lambda *_: callback(value)

            button.bind(on_release=make_callback(option))
            row.add_widget(button)
            buttons.append(button)

        setattr(self, attr_name, buttons)
        self._update_toggle_style(buttons, None)

        return row

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
            if button.text == selected_value:
                button.line_color = highlight
                button.text_color = highlight
                button.md_bg_color = (1, 0.93, 0.93, 1)
            else:
                button.line_color = neutral_line
                button.text_color = primary
                button.md_bg_color = (1, 1, 1, 1)

    def on_pre_enter(self):
        app = get_app_state()
        settings = getattr(app, "current_match_settings", None)
        self.refresh_opponent_menu()
        if not settings:
            # 初期設定がなければ入力を促すメッセージを表示
            self.status_label.text = get_text("match_entry.status_missing_setup")
            self.last_record_data = None
            if hasattr(self, "last_record_label"):
                self.last_record_label.text = get_text("match_entry.last_record_empty")
            if hasattr(self, "copy_last_button"):
                self.copy_last_button.disabled = True
            return

        # 最新の対戦カウントと使用デッキをステータスに反映
        self.status_label.text = get_text("match_entry.status_summary").format(
            count=app.current_match_count,
            deck_name=settings["deck_name"],
        )
        self.reset_inputs(focus_opponent=True)
        self._load_last_record()

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

        # 必須選択がすべて揃っているか順番に確認
        if not self.turn_choice:
            toast(get_text("match_entry.toast_select_turn"))
            return

        if not self.result_choice:
            toast(get_text("match_entry.toast_select_result"))
            return

        # 入力内容を一つの辞書にまとめて保存
        db = getattr(app, "db", None)
        if db is None:
            toast(get_text("common.db_error"))
            return

        record = {
            "match_no": app.current_match_count,
            "deck_name": settings["deck_name"],
            "turn": self.turn_choice,
            "opponent_deck": self.opponent_field.text.strip(),
            "keywords": [kw.strip() for kw in self.keyword_field.text.split(",") if kw.strip()],
            "result": self.result_choice,
        }

        try:
            db.record_match(record)
        except DatabaseError:
            toast(get_text("common.db_error"))
            return

        app.match_records = db.fetch_matches()
        app.opponent_decks = db.fetch_opponent_decks()
        self.refresh_opponent_menu()

        # 試合数をカウントアップし、画面表示と入力欄を更新
        app.current_match_count += 1
        settings["count"] = app.current_match_count
        self.status_label.text = get_text("match_entry.status_summary").format(
            count=app.current_match_count,
            deck_name=settings["deck_name"],
        )
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


class StatsScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_deck = None
        self.deck_menu = None

        # 統計情報を表示するラベルを初期化
        self.stats_label = MDLabel(
            text=get_text("stats.no_data"),
            theme_text_color="Secondary",
        )

        # 絞り込みに利用するボタンを準備
        self.filter_button = MDRaisedButton(
            text=get_text("stats.filter_button"),
            on_press=lambda *_: self.open_deck_menu(),
        )

        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        layout.add_widget(
            build_header(
                get_text("stats.header_title"),
                lambda: self.change_screen("menu"),
            )
        )
        layout.add_widget(self.filter_button)
        layout.add_widget(
            MDFlatButton(
                text=get_text("common.clear_filter"),
                on_press=lambda *_: self.clear_filter(),
            )
        )
        layout.add_widget(self.stats_label)
        layout.add_widget(
            MDFlatButton(
                text=get_text("common.return_to_top"),
                on_press=lambda *_: self.change_screen("menu"),
            )
        )

        self.add_widget(layout)

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
        win_value, _ = get_text("match_entry.result_options")
        wins = sum(1 for r in records if r["result"] == win_value)
        losses = total - wins
        win_rate = (wins / total) * 100

        # 集計結果を見やすい文字列にまとめてラベルへ反映
        header = get_text("stats.filter_label").format(
            deck_name=self.selected_deck or get_text("stats.filter_all")
        )
        self.stats_label.text = get_text("stats.summary_template").format(
            header=header,
            total=total,
            wins=wins,
            losses=losses,
            win_rate=win_rate,
        )


class SettingsScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.confirm_dialog: MDDialog | None = None

        # 設定項目を縦方向に並べるレイアウト
        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        layout.add_widget(
            build_header(
                get_text("settings.header_title"),
                lambda: self.change_screen("menu"),
            )
        )
        layout.add_widget(
            MDLabel(
                text=get_text("common.app_settings"),
                theme_text_color="Secondary",
            )
        )
        layout.add_widget(self._build_database_section())
        layout.add_widget(
            MDRaisedButton(
                text=get_text("common.exit"),
                on_press=lambda *_: self.exit_app(),
            )
        )
        layout.add_widget(
            MDFlatButton(
                text=get_text("common.return_to_top"),
                on_press=lambda *_: self.change_screen("menu"),
            )
        )
        self.add_widget(layout)

    def _build_database_section(self):
        card = MDCard(
            orientation="vertical",
            padding=(dp(16), dp(16), dp(16), dp(16)),
            size_hint=(1, None),
            radius=[16, 16, 16, 16],
        )
        card.spacing = dp(12)
        card.add_widget(
            MDLabel(
                text=get_text("settings.db_section_title"),
                font_style="Subtitle1",
            )
        )
        card.add_widget(
            MDLabel(
                text=get_text("settings.db_init_description"),
                theme_text_color="Secondary",
            )
        )
        card.add_widget(
            MDRaisedButton(
                text=get_text("settings.db_init_button"),
                on_press=lambda *_: self.open_db_init_dialog(),
            )
        )
        return card

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
        self.db = DatabaseManager()
        self.db.ensure_database()
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
        sm = MDScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(DeckRegistrationScreen(name="deck_register"))
        sm.add_widget(SeasonRegistrationScreen(name="season_register"))
        sm.add_widget(MatchSetupScreen(name="match_setup"))
        sm.add_widget(MatchEntryScreen(name="match_entry"))
        sm.add_widget(StatsScreen(name="stats"))
        sm.add_widget(SettingsScreen(name="settings"))
        return sm

if __name__ == '__main__':
    DeckAnalyzerApp().run()
