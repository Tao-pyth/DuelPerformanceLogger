from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.gridlayout import MDGridLayout
from kivymd.uix.card import MDCard
from kivymd.uix.label import MDLabel, MDIcon
from kivymd.uix.button import MDRaisedButton, MDFlatButton
from kivymd.uix.toolbar import MDToolbar
from kivy.uix.scrollview import ScrollView
from kivy.uix.widget import Widget
from kivy.metrics import dp
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.core.window import Window
from function.clas.deck_manager import DeckManagerScreen
from function.clas.card_list_screen import CardListScreen

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
                on_press=lambda *_: self.change_screen("match"),
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
                icon="clipboard-text",
                title="試合データ登録",
                description="対戦結果やメモを残して成長の記録を作成します。",
                screen_name="match",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="chart-areaspline",
                title="統計表示",
                description="勝率や使用カードの傾向をグラフで確認しましょう。",
                screen_name="stats",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="cards",
                title="デッキ管理",
                description="デッキリストを編集し、カードの構成を整理します。",
                screen_name="deck_manager",
            )
        )
        grid.add_widget(
            self._create_menu_option(
                icon="view-list",
                title="カード一覧",
                description="収集カードを確認し検索するためのリファレンスです。",
                screen_name="card_list",
            )
        )
        grid.add_widget(
            self._create_exit_card()
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

    def _create_exit_card(self):
        card = MDCard(
            orientation="vertical",
            padding=(dp(20), dp(20), dp(20), dp(20)),
            size_hint=(1, None),
            height=dp(140),
            radius=[18, 18, 18, 18],
            elevation=2,
        )
        card.add_widget(
            MDLabel(
                text="アプリを終了",
                font_style="H6",
                theme_text_color="Primary",
            )
        )
        card.add_widget(
            MDLabel(
                text="作業が終わったら安全にアプリケーションを終了します。",
                theme_text_color="Secondary",
            )
        )

        button_row = MDBoxLayout(size_hint_y=None, height=dp(48), padding=(0, dp(12), 0, 0))
        button_row.add_widget(Widget())
        button_row.add_widget(
            MDRaisedButton(
                text="終了",
                on_press=self.exit_app,
            )
        )
        card.add_widget(button_row)
        return card

    def change_screen(self, screen_name):
        if self.manager:
            self.manager.current = screen_name

    def exit_app(self, *_) -> None:
        MDApp.get_running_app().stop()
        Window.close()

class MatchRegisterScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)
        layout.add_widget(MDLabel(text="[試合データ登録画面]", halign="center"))
        layout.add_widget(MDRaisedButton(text="戻る", on_press=lambda x: self.change_screen("menu")))
        self.add_widget(layout)

    def change_screen(self, screen_name):
        self.manager.current = screen_name

class StatsScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)
        layout.add_widget(MDLabel(text="[統計表示画面]", halign="center"))
        layout.add_widget(MDRaisedButton(text="戻る", on_press=lambda x: self.change_screen("menu")))
        self.add_widget(layout)

    def change_screen(self, screen_name):
        self.manager.current = screen_name

class DeckAnalyzerApp(MDApp):
    def build(self):
        self.theme_cls.primary_palette = "BlueGray"
        sm = MDScreenManager()
        sm.add_widget(MenuScreen(name="menu"))
        sm.add_widget(MatchRegisterScreen(name="match"))
        sm.add_widget(StatsScreen(name="stats"))
        sm.add_widget(DeckManagerScreen(name="deck_manager"))
        sm.add_widget(CardListScreen(name="card_list"))
        return sm

if __name__ == '__main__':
    DeckAnalyzerApp().run()
