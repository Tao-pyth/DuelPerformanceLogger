"""Base classes and shared UI helpers for application screens."""

from __future__ import annotations

from typing import Callable

from kivy.metrics import dp
from kivy.uix.widget import Widget
from kivy.core.window import Window
from kivymd.uix.screen import MDScreen
from kivymd.uix.anchorlayout import MDAnchorLayout
from kivymd.uix.boxlayout import MDBoxLayout
from kivymd.uix.button import MDRectangleFlatIconButton
from kivymd.uix.label import MDLabel

from function.cmn_app_state import get_app_state
from function.cmn_resources import get_text


def resolve_screen_name(screen_name: str, *, mode: str | None = None) -> str:
    """Resolve the actual screen name based on the current UI mode."""

    if screen_name in {"match_setup", "match_entry"}:
        if mode is None:
            app = get_app_state()
            mode = getattr(app, "ui_mode", "normal")
        if mode == "broadcast":
            return f"{screen_name}_broadcast"
    return screen_name


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

        def _sync_width(instance, value):  # type: ignore[unused-arg]
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


class BaseManagedScreen(MDScreen):
    """Base class providing a scaffold and navigation helpers for screens."""

    def _create_scaffold(
        self,
        title: str,
        back_callback: Callable | None = None,
        top_callback: Callable | None = None,
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
        """Navigate to the target screen if available."""

        if self.manager:
            mode_hint = getattr(self, "screen_mode", None)
            resolved = resolve_screen_name(screen_name, mode=mode_hint)
            self.manager.current = resolved

    def _sync_window_size(self, mode: str) -> None:
        """Adjust the window size according to the given mode."""

        app = get_app_state()
        default_size = getattr(app, "default_window_size", Window.size)

        if mode == "broadcast":
            target_size = (1080, 280)
        else:
            target_size = default_size

        if tuple(Window.size) != tuple(target_size):
            Window.size = target_size


__all__ = ["BaseManagedScreen", "build_header", "resolve_screen_name"]
