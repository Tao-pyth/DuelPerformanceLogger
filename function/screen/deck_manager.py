from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton

from function.cmn_resources import get_text


class DeckManagerScreen(MDScreen):
    """プレースホルダーのデッキ管理画面."""

    # NOTE: 将来的にデッキ編集機能を実装する予定の画面です。現段階では
    # サンプル UI と戻るボタンのみが配置されており、画面遷移の仕組みを
    # 理解する助けとなるよう簡潔にまとめています。

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        layout = MDBoxLayout(orientation="vertical", spacing=24, padding=(24, 24, 24, 24))
        layout.add_widget(
            MDLabel(
                text=get_text("placeholders.deck_manager"),
                halign="center",
                font_style="H5",
            )
        )
        layout.add_widget(
            MDRaisedButton(
                text=get_text("common.back_to_menu"),
                pos_hint={"center_x": 0.5},
                on_press=lambda *_: self._back_to_menu(),
            )
        )
        self.add_widget(layout)

    def _back_to_menu(self):
        # ScreenManager が存在する場合のみメニューへ戻る。
        if self.manager:
            self.manager.current = "menu"
