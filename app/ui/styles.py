"""
Modern dark theme stylesheets and UI styling for R.I.A.T.A v0.1.0
Author: Ali Kamrani (MRThugh)
"""

MAIN_STYLESHEET = """
QMainWindow {
    background-color: #0b0f19;
}

QWidget {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Vazirmatn", "IRANSans", Ubuntu, Helvetica, Arial, sans-serif;
    color: #e2e8f0;
}

/* Header styling */
#headerWidget {
    background-color: #111827;
    border-bottom: 1px solid #1f2937;
    padding: 10px 16px;
}

#appTitle {
    font-size: 18px;
    font-weight: 700;
    color: #38bdf8;
    letter-spacing: 1px;
}

#appSubtitle {
    font-size: 11px;
    color: #94a3b8;
    font-weight: 400;
}

#statusDot {
    color: #10b981;
    font-size: 14px;
    font-weight: bold;
}

#statusText {
    color: #10b981;
    font-size: 11px;
    font-weight: 600;
    letter-spacing: 0.5px;
}

#dryRunBadge {
    background-color: #78350f;
    color: #fde68a;
    border: 1px solid #b45309;
    border-radius: 4px;
    padding: 2px 8px;
    font-size: 10px;
    font-weight: 700;
}

#headerBtn {
    background-color: #1f2937;
    color: #cbd5e1;
    border: 1px solid #374151;
    border-radius: 6px;
    padding: 5px 12px;
    font-size: 11px;
    font-weight: 500;
}

#headerBtn:hover {
    background-color: #374151;
    color: #f8fafc;
}

#headerBtn:pressed {
    background-color: #111827;
}

/* Chat container and scroll area */
QScrollArea {
    background-color: #0b0f19;
    border: none;
}

#scrollContent {
    background-color: #0b0f19;
}

QScrollBar:vertical {
    border: none;
    background: #0b0f19;
    width: 6px;
    margin: 0px;
}

QScrollBar::handle:vertical {
    background: #334155;
    border-radius: 3px;
    min-height: 20px;
}

QScrollBar::handle:vertical:hover {
    background: #475569;
}

QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
    height: 0px;
}

/* User Message Bubble */
#userMessageBubble {
    background-color: #1e3a8a;
    border: 1px solid #2563eb;
    border-radius: 12px;
    padding: 10px 14px;
}

#userMessageText {
    color: #ffffff;
    font-size: 13px;
    line-height: 1.4;
}

/* Assistant Message Bubble */
#assistantMessageBubble {
    background-color: #161e2e;
    border: 1px solid #273549;
    border-radius: 12px;
    padding: 12px 16px;
}

#assistantMessageText {
    color: #e2e8f0;
    font-size: 13px;
    line-height: 1.5;
}

#assistantHeader {
    color: #38bdf8;
    font-size: 11px;
    font-weight: 700;
    letter-spacing: 0.5px;
    margin-bottom: 4px;
}

#intentBadge {
    background-color: #0f172a;
    border: 1px solid #334155;
    color: #38bdf8;
    border-radius: 4px;
    padding: 2px 6px;
    font-size: 10px;
    font-family: monospace;
}

#timestampLabel {
    color: #64748b;
    font-size: 10px;
}

/* Input Widget */
#inputAreaWidget {
    background-color: #111827;
    border-top: 1px solid #1f2937;
    padding: 12px 16px;
}

#messageInput {
    background-color: #1e293b;
    color: #f8fafc;
    border: 1px solid #334155;
    border-radius: 8px;
    padding: 8px 12px;
    font-size: 13px;
    selection-background-color: #38bdf8;
}

#messageInput:focus {
    border: 1px solid #0284c7;
    background-color: #1a2333;
}

#sendButton {
    background-color: #0284c7;
    color: #ffffff;
    border: none;
    border-radius: 8px;
    padding: 8px 18px;
    font-size: 13px;
    font-weight: 600;
}

#sendButton:hover {
    background-color: #0369a1;
}

#sendButton:pressed {
    background-color: #075985;
}

#sendButton:disabled {
    background-color: #334155;
    color: #94a3b8;
}

#emptyStateLabel {
    color: #64748b;
    font-size: 14px;
    padding: 40px;
}
"""
