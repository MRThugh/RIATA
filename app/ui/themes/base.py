"""
Theme definitions for R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)
"""

from dataclasses import dataclass


@dataclass
class ThemeColors:
    """Color palette tokens for R.I.A.T.A desktop themes."""

    # Backgrounds & Surfaces
    bg_primary: str
    bg_secondary: str
    bg_surface: str
    bg_elevated: str
    bg_hover: str
    bg_selected: str

    # Borders & Dividers
    border_subtle: str
    border_muted: str
    border_active: str

    # Text & Content
    text_primary: str
    text_secondary: str
    text_muted: str
    text_inverse: str

    # Brand & Accents
    accent_primary: str
    accent_hover: str
    accent_active: str
    accent_glow: str

    # Feedback & Status
    status_online: str
    status_dry_run_bg: str
    status_dry_run_text: str
    status_dry_run_border: str
    status_error_bg: str
    status_error_text: str
    status_success: str

    # Chat Specific
    bubble_user: str
    bubble_user_border: str
    bubble_user_text: str
    bubble_assistant: str
    bubble_assistant_border: str
    bubble_assistant_text: str
    bubble_badge_bg: str
    bubble_badge_text: str

    # Input & Controls
    input_bg: str
    input_border: str
    input_focus_border: str
    scrollbar_track: str
    scrollbar_thumb: str
    scrollbar_thumb_hover: str
