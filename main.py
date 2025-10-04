from kivymd.app import MDApp
from kivymd.uix.screenmanager import MDScreenManager
from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton
from kivy.core.text import LabelBase, DEFAULT_FONT
from kivy.core.window import Window
from function.clas.deck_manager import DeckManagerScreen
from function.clas.card_list_screen import CardListScreen

# 日本語フォント設定
LabelBase.register(DEFAULT_FONT, r'resource\\theme\\font\\mgenplus-1c-regular.ttf')

class MenuScreen(MDScreen):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation='vertical', spacing=10, padding=20)
        layout.add_widget(MDLabel(text="デッキ分析ツール メインメニュー", halign="center", font_style="H5"))
        layout.add_widget(MDRaisedButton(text="試合データ登録", on_press=lambda x: self.change_screen("match")))
        layout.add_widget(MDRaisedButton(text="統計表示", on_press=lambda x: self.change_screen("stats")))
        layout.add_widget(MDRaisedButton(text="終了", on_press=self.exit_app))
        self.add_widget(layout)

    def change_screen(self, screen_name):
        self.manager.current = screen_name

    def exit_app(self, instance):
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
        return sm

if __name__ == '__main__':
    DeckAnalyzerApp().run()
