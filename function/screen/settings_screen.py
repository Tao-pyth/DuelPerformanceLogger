"""Application settings screen."""

from __future__ import annotations

from kivy.metrics import dp
from kivy.uix.scrollview import ScrollView
from kivy.core.window import Window
from kivymd.app import MDApp
from kivymd.toast import toast
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDFlatButton, MDRaisedButton, MDRectangleFlatIconButton
from kivymd.uix.card import MDCard
from kivymd.uix.dialog import MDDialog
from kivymd.uix.label import MDLabel

from function.cmn_app_state import get_app_state, get_fallback_state
from function.cmn_resources import get_text

from .base import BaseManagedScreen


class SettingsScreen(BaseManagedScreen):
    """アプリ全体の設定（UI モード、バックアップ等）を扱う画面。"""

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

        # 設定項目を縦に並べるスクロールコンテナを構築。
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
        # 現在の UI モードとバックアップ日時を画面表示に反映。
        app = get_app_state()
        mode = getattr(app, "ui_mode", "normal")
        self._update_mode_buttons(mode)
        self._update_backup_label()

    def _build_database_section(self):
        """バックアップや初期化操作をまとめたカードを生成。"""

        card = MDCard(
            orientation="vertical",
            padding=(dp(16), dp(16), dp(16), dp(16)),
            size_hint=(1, None),
            radius=[16, 16, 16, 16],
        )
        card.spacing = dp(12)
        card.bind(minimum_height=card.setter("height"))
        title_label = MDLabel(
            text=get_text("settings.db_section_title"),
            font_style="Subtitle1",
            halign="left",
        )
        self._configure_label(title_label)
        card.add_widget(title_label)
        description_label = MDLabel(
            text=get_text("settings.backup_description"),
            theme_text_color="Secondary",
            halign="left",
        )
        self._configure_label(description_label)
        card.add_widget(description_label)
        self.backup_info_label = MDLabel(
            text="",
            theme_text_color="Hint",
            halign="left",
        )
        self._configure_label(self.backup_info_label)
        card.add_widget(self.backup_info_label)
        backup_button = MDRaisedButton(
            text=get_text("settings.backup_button"),
            on_press=lambda *_: self.create_backup(),
        )
        backup_button.size_hint = (1, None)
        backup_button.height = dp(48)
        card.add_widget(backup_button)
        init_description_label = MDLabel(
            text=get_text("settings.db_init_description"),
            theme_text_color="Secondary",
            halign="left",
        )
        self._configure_label(init_description_label)
        card.add_widget(init_description_label)
        init_button = MDRaisedButton(
            text=get_text("settings.db_init_button"),
            on_press=lambda *_: self.open_db_init_dialog(),
        )
        init_button.size_hint = (1, None)
        init_button.height = dp(48)
        card.add_widget(init_button)
        return card

    def _build_ui_section(self):
        """UI モード切り替え用のカードを生成。"""

        card = MDCard(
            orientation="vertical",
            padding=(dp(16), dp(16), dp(16), dp(16)),
            size_hint=(1, None),
            radius=[16, 16, 16, 16],
        )
        card.spacing = dp(12)
        card.bind(minimum_height=card.setter("height"))
        title_label = MDLabel(
            text=get_text("settings.ui_section_title"),
            font_style="Subtitle1",
            halign="left",
        )
        self._configure_label(title_label)
        card.add_widget(title_label)
        description_label = MDLabel(
            text=get_text("settings.ui_mode_description"),
            theme_text_color="Secondary",
            halign="left",
        )
        self._configure_label(description_label)
        card.add_widget(description_label)

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

    def _set_ui_mode(self, mode: str) -> None:
        """UI モードを更新し、アプリ状態および DB へ反映する。"""

        app = get_app_state()
        app.ui_mode = mode
        db = getattr(app, "db", None)
        if db is not None:
            db.set_ui_mode(mode)
        fallback = get_fallback_state()
        fallback.ui_mode = mode
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
        """最新のバックアップパスを表示用ラベルへ反映。"""

        if not self.backup_info_label:
            return
        app = get_app_state()
        db = getattr(app, "db", None)
        last_backup = None
        if db is not None:
            last_backup = db.get_metadata("last_backup")
        if last_backup:
            self.backup_info_label.text = get_text("settings.last_backup").format(
                path=last_backup
            )
        else:
            self.backup_info_label.text = get_text("settings.no_backup")

    def create_backup(self) -> None:
        """CSV バックアップを作成し、保存場所をユーザーへ知らせる。"""

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

        db.record_backup_path(backup_path)
        self._update_backup_label()
        toast(get_text("settings.backup_success"))

    def open_db_init_dialog(self):
        """DB 初期化を実行するか確認するダイアログを表示。"""

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
        """ユーザーの確認後にデータベース初期化を実行。"""

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
            fallback = get_fallback_state()
            fallback.db = db
            fallback.decks = []
            fallback.seasons = []
            fallback.match_records = []
            fallback.current_match_settings = None
            fallback.current_match_count = 0
            fallback.opponent_decks = []
        except Exception:  # pragma: no cover - defensive
            toast(get_text("settings.db_init_failure"))
            return

        toast(get_text("settings.db_init_success"))

    def exit_app(self):
        """アプリケーションを安全に終了させる。"""

        self._dismiss_dialog()
        app = MDApp.get_running_app()
        if app:
            app.stop()
        Window.close()


__all__ = ["SettingsScreen"]
