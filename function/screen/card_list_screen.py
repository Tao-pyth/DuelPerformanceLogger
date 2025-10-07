from kivymd.uix.screen import MDScreen
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.label import MDLabel
from kivymd.uix.button import MDRaisedButton

from function.cmn_resources import get_text


class CardListScreen(MDScreen):
    """プレースホルダーのカードリスト画面."""

    # NOTE: まだ実装されていない画面のサンプルとして配置されているクラス。
    # 画面切り替えやレイアウト構築の流れを最小構成で学べるように、簡潔な
    # UI と戻るボタンのみで構成されています。

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # 画面全体を縦方向レイアウトで構築。`spacing` や `padding` を使うと
        # 要素間の余白を簡単に調整できます。
        layout = MDBoxLayout(orientation="vertical", spacing=24, padding=(24, 24, 24, 24))
        layout.add_widget(
            MDLabel(
                text=get_text("placeholders.card_list"),
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
        # ScreenManager が設定されていればメニュー画面へ戻る。
        if self.manager:
            self.manager.current = "menu"
