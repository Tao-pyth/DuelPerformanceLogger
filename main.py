from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.textfield import MDTextField
from kivymd.uix.menu import MDDropdownMenu
from kivymd.uix.list import OneLineListItem
from kivymd.uix.chip import MDChip
from kivymd.uix.toolbar import MDToolbar
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.core.window import Window
from kivymd.toast import toast

# 日本語フォント設定
LabelBase.register(DEFAULT_FONT, r'resource\\theme\\font\\mgenplus-1c-regular.ttf')

class MenuScreen(MDScreen):
    """アプリケーションの初期画面."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        root_layout = MDBoxLayout(orientation="vertical", spacing=0)

        toolbar = MDToolbar(title="デュエルパフォーマンスログ")
        toolbar.elevation = 10
        root_layout.add_widget(toolbar)

        scroll_view = ScrollView()
        content = MDBoxLayout(
            orientation="vertical",
            padding=(dp(24), dp(24), dp(24), dp(32)),
            spacing=dp(24),
            size_hint_y=None,
        )
        content.bind(minimum_height=content.setter("height"))

        content.add_widget(self._build_hero_card())
        content.add_widget(self._build_navigation_grid())

        content.add_widget(
            MDLabel(
                text="バージョン 0.1.0",
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
                text="デッキ分析ツールへようこそ",
                font_style="H4",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
            )
        )
        card.add_widget(
            MDLabel(
                text=(
                    "試合結果とカード情報をまとめて管理し、\n"
                    "デッキの改善ポイントを見つけましょう。"
                ),
                theme_text_color="Custom",
                text_color=(1, 1, 1, 0.85),
            )
        )

        actions = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(48))
        actions.add_widget(
            MDRaisedButton(
                text="試合を記録する",
                on_press=lambda *_: self.change_screen("match_setup"),
            )
        )
        actions.add_widget(
            MDFlatButton(
                text="統計を見る",
                theme_text_color="Custom",
                text_color=(1, 1, 1, 1),
                on_press=lambda *_: self.change_screen("stats"),
            )
        )
        card.add_widget(actions)

        return card

    def _build_navigation_grid(self):
        grid = MDGridLayout(
            cols=1,
            spacing=dp(16),
            size_hint_y=None,
            adaptive_height=True,
        )

        grid.add_widget(
            self._create_menu_option(
                icon="cards",
                title="使用デッキ情報登録",
                description="対戦で使用するデッキの名称と説明を管理します。",
                screen_name="deck_register",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="calendar",
                title="シーズン情報登録",
                description="大会や期間の情報をまとめて記録します。",
                screen_name="season_register",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="clipboard-text",
                title="対戦データ入力",
                description="試合の初期情報を設定して記録を始めます。",
                screen_name="match_setup",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="chart-areaspline",
                title="対戦結果統計",
                description="条件で絞り込んだ勝率などの統計を確認します。",
                screen_name="stats",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="cog",
                title="設定",
                description="終了操作などの各種設定を行います。",
                screen_name="settings",
            )
        )

        return grid

    def _create_menu_option(self, icon, title, description, screen_name):
        card = MDCard(
            orientation="vertical",
            padding=(dp(20), dp(20), dp(20), dp(20)),
            size_hint=(1, None),
            height=dp(180),
            radius=[18, 18, 18, 18],
            elevation=2,
        )

        header = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(36))
        header.add_widget(MDIcon(icon=icon, size_hint=(None, None), size=(dp(36), dp(36))))
        header.add_widget(
            MDLabel(
                text=title,
                font_style="H6",
                theme_text_color="Primary",
            )
        )
        card.add_widget(header)

        card.add_widget(
            MDLabel(
                text=description,
                theme_text_color="Secondary",
            )
        )

        button_row = MDBoxLayout(size_hint_y=None, height=dp(48), padding=(0, dp(12), 0, 0))
        button_row.add_widget(Widget())
        button_row.add_widget(
            MDRaisedButton(
                text="開く",
                on_press=lambda *_: self.change_screen(screen_name),
            )
        )
        card.add_widget(button_row)

        return card

    def change_screen(self, screen_name):
        if self.manager:
            self.manager.current = screen_name

class BaseManagedScreen(MDScreen):
    def change_screen(self, screen_name):
        if self.manager:
            self.manager.current = screen_name


class DeckRegistrationScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.name_field = MDTextField(
            hint_text="デッキ名",
            helper_text="必須項目です",
            helper_text_mode="on_focus",
        )
        self.description_field = MDTextField(
            hint_text="デッキ説明",
            multiline=True,
            max_text_length=200,
        )
        self.deck_list_label = MDLabel(
            text="登録済みデッキはありません",
            theme_text_color="Hint",
        )

        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        layout.add_widget(self._build_toolbar("使用デッキ情報登録"))
        layout.add_widget(self.name_field)
        layout.add_widget(self.description_field)
        layout.add_widget(
            MDRaisedButton(text="登録する", on_press=lambda *_: self.register_deck())
        )
        layout.add_widget(self.deck_list_label)

        back_button = MDFlatButton(text="トップに戻る", on_press=lambda *_: self.change_screen("menu"))
        layout.add_widget(back_button)

        self.add_widget(layout)

    def _build_toolbar(self, title):
        toolbar = MDToolbar(title=title)
        toolbar.left_action_items = [["arrow-left", lambda *_: self.change_screen("menu")]]
        return toolbar

    def register_deck(self):
        name = self.name_field.text.strip()
        description = self.description_field.text.strip()

        if not name:
            toast("デッキ名を入力してください")
            return

        app = MDApp.get_running_app()
        if any(deck["name"] == name for deck in app.decks):
            toast("同じ名前のデッキが既に登録されています")
            return

        app.decks.append({"name": name, "description": description})
        toast("デッキを登録しました")
        self.name_field.text = ""
        self.description_field.text = ""
        self.update_deck_list()

    def on_pre_enter(self):
        self.update_deck_list()

    def update_deck_list(self):
        app = MDApp.get_running_app()
        if not app.decks:
            self.deck_list_label.text = "登録済みデッキはありません"
        else:
            lines = [f"• {deck['name']}: {deck['description'] or '説明なし'}" for deck in app.decks]
            self.deck_list_label.text = "\n".join(lines)


class SeasonRegistrationScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        self.name_field = MDTextField(
            hint_text="シーズン名",
            helper_text="必須項目です",
            helper_text_mode="on_focus",
        )
        self.description_field = MDTextField(
            hint_text="シーズン説明",
            multiline=True,
            max_text_length=200,
        )
        self.season_list_label = MDLabel(
            text="登録済みシーズンはありません",
            theme_text_color="Hint",
        )

        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        layout.add_widget(self._build_toolbar("シーズン情報登録"))
        layout.add_widget(self.name_field)
        layout.add_widget(self.description_field)
        layout.add_widget(
            MDRaisedButton(text="登録する", on_press=lambda *_: self.register_season())
        )
        layout.add_widget(self.season_list_label)
        layout.add_widget(MDFlatButton(text="トップに戻る", on_press=lambda *_: self.change_screen("menu")))

        self.add_widget(layout)

    def _build_toolbar(self, title):
        toolbar = MDToolbar(title=title)
        toolbar.left_action_items = [["arrow-left", lambda *_: self.change_screen("menu")]]
        return toolbar

    def register_season(self):
        name = self.name_field.text.strip()
        description = self.description_field.text.strip()

        if not name:
            toast("シーズン名を入力してください")
            return

        app = MDApp.get_running_app()
        if any(season["name"] == name for season in app.seasons):
            toast("同じ名前のシーズンが既に登録されています")
            return

        app.seasons.append({"name": name, "description": description})
        toast("シーズンを登録しました")
        self.name_field.text = ""
        self.description_field.text = ""
        self.update_season_list()

    def on_pre_enter(self):
        self.update_season_list()

    def update_season_list(self):
        app = MDApp.get_running_app()
        if not app.seasons:
            self.season_list_label.text = "登録済みシーズンはありません"
        else:
            lines = [f"• {season['name']}: {season['description'] or '説明なし'}" for season in app.seasons]
            self.season_list_label.text = "\n".join(lines)


class MatchSetupScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_deck = None
        self.deck_menu = None

        self.match_count_field = MDTextField(
            hint_text="対戦カウント初期値",
            input_filter="int",
            text="0",
        )
        self.deck_button = MDRaisedButton(text="使用デッキを選択", on_press=lambda *_: self.open_deck_menu())

        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        layout.add_widget(self._build_toolbar("対戦データ入力開始"))
        layout.add_widget(self.match_count_field)
        layout.add_widget(self.deck_button)
        layout.add_widget(
            MDRaisedButton(text="入力開始", on_press=lambda *_: self.start_entry())
        )
        layout.add_widget(MDFlatButton(text="トップに戻る", on_press=lambda *_: self.change_screen("menu")))

        self.add_widget(layout)

    def _build_toolbar(self, title):
        toolbar = MDToolbar(title=title)
        toolbar.left_action_items = [["arrow-left", lambda *_: self.change_screen("menu")]]
        return toolbar

    def on_pre_enter(self):
        self.selected_deck = None
        self.deck_button.text = "使用デッキを選択"

    def open_deck_menu(self):
        app = MDApp.get_running_app()
        if not app.decks:
            toast("まずはデッキを登録してください")
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
            self.deck_menu.dismiss()

        self.deck_menu = MDDropdownMenu(caller=self.deck_button, items=menu_items, width_mult=4)
        self.deck_menu.open()

    def set_selected_deck(self, name):
        self.selected_deck = name
        self.deck_button.text = f"使用デッキ: {name}"
        if self.deck_menu:
            self.deck_menu.dismiss()

    def start_entry(self):
        if not self.selected_deck:
            toast("使用デッキを選択してください")
            return

        try:
            initial_count = int(self.match_count_field.text or 0)
        except ValueError:
            toast("対戦カウントには数字を入力してください")
            return

        app = MDApp.get_running_app()
        app.current_match_settings = {
            "count": initial_count,
            "deck_name": self.selected_deck,
        }
        app.current_match_count = initial_count

        toast("対戦データ入力を開始します")
        self.change_screen("match_entry")


class MatchEntryScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.turn_choice = None
        self.result_choice = None
        self.turn_chips = []
        self.result_chips = []

        self.status_label = MDLabel(text="対戦データ入力を開始してください", halign="center")
        self.opponent_field = MDTextField(hint_text="対戦相手使用デッキ")
        self.keyword_field = MDTextField(
            hint_text="キーワード (カンマ区切り)",
            multiline=True,
        )

        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        layout.add_widget(self._build_toolbar("対戦データ入力"))
        layout.add_widget(self.status_label)
        layout.add_widget(MDLabel(text="先攻/後攻を選択", theme_text_color="Secondary"))
        layout.add_widget(self._build_chip_row(["先攻", "後攻"], self.set_turn_choice))
        layout.add_widget(self.opponent_field)
        layout.add_widget(self.keyword_field)
        layout.add_widget(MDLabel(text="対戦結果を選択", theme_text_color="Secondary"))
        layout.add_widget(self._build_result_row())
        layout.add_widget(
            MDRaisedButton(text="結果を記録", on_press=lambda *_: self.submit_match())
        )
        layout.add_widget(MDFlatButton(text="開始画面に戻る", on_press=lambda *_: self.change_screen("match_setup")))

        self.add_widget(layout)

    def _build_toolbar(self, title):
        toolbar = MDToolbar(title=title)
        toolbar.left_action_items = [["arrow-left", lambda *_: self.change_screen("match_setup")]]
        return toolbar

    def _build_chip_row(self, options, callback):
        row = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(40))
        if callback == self.set_turn_choice:
            self.turn_chips = []
        chips = []
        for option in options:
            chip = MDChip(text=option, check=True)
            chip.bind(on_release=lambda chip, value=option: callback(value))
            row.add_widget(chip)
            chips.append(chip)

        if callback == self.set_turn_choice:
            self.turn_chips = chips
        return row

    def _build_result_row(self):
        row = MDBoxLayout(spacing=dp(12), size_hint_y=None, height=dp(40))
        self.result_chips = []
        for option in ["勝ち", "負け"]:
            chip = MDChip(text=option, check=True)
            chip.bind(on_release=lambda chip, value=option: self.set_result_choice(value))
            row.add_widget(chip)
            self.result_chips.append(chip)
        return row

    def on_pre_enter(self):
        app = MDApp.get_running_app()
        settings = getattr(app, "current_match_settings", None)
        if not settings:
            self.status_label.text = "開始画面から初期情報を設定してください"
            return

        self.status_label.text = (
            f"対戦カウント: {app.current_match_count} / 使用デッキ: {settings['deck_name']}"
        )
        self.reset_inputs()

    def set_turn_choice(self, choice):
        self.turn_choice = choice
        for chip in self.turn_chips:
            chip.active = chip.text == choice

    def set_result_choice(self, choice):
        self.result_choice = choice
        for chip in self.result_chips:
            chip.active = chip.text == choice

    def submit_match(self):
        app = MDApp.get_running_app()
        settings = getattr(app, "current_match_settings", None)
        if not settings:
            toast("開始画面で初期情報を設定してください")
            return

        if not self.turn_choice:
            toast("先攻/後攻を選択してください")
            return

        if not self.result_choice:
            toast("対戦結果を選択してください")
            return

        record = {
            "match_no": app.current_match_count,
            "deck_name": settings["deck_name"],
            "turn": self.turn_choice,
            "opponent_deck": self.opponent_field.text.strip(),
            "keywords": [kw.strip() for kw in self.keyword_field.text.split(",") if kw.strip()],
            "result": self.result_choice,
        }
        app.match_records.append(record)

        app.current_match_count += 1
        self.status_label.text = (
            f"対戦カウント: {app.current_match_count} / 使用デッキ: {settings['deck_name']}"
        )
        self.reset_inputs()
        toast("対戦結果を記録しました")

    def reset_inputs(self):
        self.turn_choice = None
        self.result_choice = None
        for chip in self.turn_chips:
            chip.active = False
        for chip in self.result_chips:
            chip.active = False
        self.opponent_field.text = ""
        self.keyword_field.text = ""


class StatsScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.selected_deck = None
        self.deck_menu = None

        self.stats_label = MDLabel(
            text="まだ統計を表示できるデータがありません",
            theme_text_color="Secondary",
        )

        self.filter_button = MDRaisedButton(
            text="使用デッキで絞り込み",
            on_press=lambda *_: self.open_deck_menu(),
        )

        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        layout.add_widget(self._build_toolbar("対戦結果統計"))
        layout.add_widget(self.filter_button)
        layout.add_widget(
            MDFlatButton(text="絞り込み解除", on_press=lambda *_: self.clear_filter())
        )
        layout.add_widget(self.stats_label)
        layout.add_widget(MDFlatButton(text="トップに戻る", on_press=lambda *_: self.change_screen("menu")))

        self.add_widget(layout)

    def _build_toolbar(self, title):
        toolbar = MDToolbar(title=title)
        toolbar.left_action_items = [["arrow-left", lambda *_: self.change_screen("menu")]]
        return toolbar

    def on_pre_enter(self):
        self.update_stats()

    def open_deck_menu(self):
        app = MDApp.get_running_app()
        if not app.decks:
            toast("デッキが登録されていません")
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
            self.deck_menu.dismiss()

        self.deck_menu = MDDropdownMenu(caller=self.filter_button, items=menu_items, width_mult=4)
        self.deck_menu.open()

    def set_deck_filter(self, name):
        self.selected_deck = name
        if self.deck_menu:
            self.deck_menu.dismiss()
        self.filter_button.text = f"絞り込み: {name}"
        self.update_stats()

    def clear_filter(self):
        self.selected_deck = None
        self.filter_button.text = "使用デッキで絞り込み"
        self.update_stats()

    def update_stats(self):
        app = MDApp.get_running_app()
        records = app.match_records
        if self.selected_deck:
            records = [r for r in records if r["deck_name"] == self.selected_deck]

        if not records:
            if self.selected_deck:
                self.stats_label.text = f"{self.selected_deck} のデータはまだありません"
            else:
                self.stats_label.text = "まだ統計を表示できるデータがありません"
            return

        total = len(records)
        wins = sum(1 for r in records if r["result"] == "勝ち")
        losses = total - wins
        win_rate = (wins / total) * 100

        header = f"絞り込み: {self.selected_deck or 'すべてのデッキ'}"
        self.stats_label.text = (
            f"{header}\n対戦数: {total}\n勝利: {wins}\n敗北: {losses}\n勝率: {win_rate:.1f}%"
        )


class SettingsScreen(BaseManagedScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", spacing=dp(16), padding=dp(24))
        toolbar = MDToolbar(title="設定")
        toolbar.left_action_items = [["arrow-left", lambda *_: self.change_screen("menu")]]
        layout.add_widget(toolbar)
        layout.add_widget(MDLabel(text="アプリケーション設定", theme_text_color="Secondary"))
        layout.add_widget(MDRaisedButton(text="終了", on_press=lambda *_: self.exit_app()))
        layout.add_widget(MDFlatButton(text="トップに戻る", on_press=lambda *_: self.change_screen("menu")))
        self.add_widget(layout)

    def exit_app(self):
        MDApp.get_running_app().stop()
        Window.close()

class DeckAnalyzerApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "BlueGray"
        self.decks = []
        self.seasons = []
        self.match_records = []
        self.current_match_settings = None
        self.current_match_count = 0
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
