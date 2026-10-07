"""
Backward compatibility facade for styles in R.I.A.T.A v0.1.1
Author: Ali Kamrani (MRThugh)

Delegates to ThemeManager to provide active theme stylesheets.
"""

from app.ui.themes.manager import get_theme_manager

# Dynamic property returning current theme's stylesheet
MAIN_STYLESHEET: str = get_theme_manager().generate_stylesheet()
