from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton


class DeckManagerScreen(MDScreen):
    """プレースホルダーのデッキ管理画面."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", spacing=24, padding=(24, 24, 24, 24))
        layout.add_widget(
            MDLabel(
                text="デッキ管理機能は現在準備中です。",
                halign="center",
                font_style="H5",
            )
        )
        layout.add_widget(
            MDRaisedButton(
                text="メニューに戻る",
                pos_hint={"center_x": 0.5},
                on_press=lambda *_: self._back_to_menu(),
            )
        )
        self.add_widget(layout)

    def _back_to_menu(self):
        if self.manager:
            self.manager.current = "menu"
