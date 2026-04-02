"""Textual theme CSS for the rich terminal interface."""

LIGHT_THEME = """
Screen {
    background: #f6f8fa;
    color: #24292f;
}
"""

DARK_THEME = """
Screen {
    background: #0d1117;
    color: #e6edf3;
}

#app-shell {
    layout: vertical;
    width: 100%;
    height: 100%;
    background: #0d1117;
}

#header-bar {
    height: 1;
    background: #161b22;
    color: #58a6ff;
    padding: 0 1;
    text-style: bold;
}

#main-row {
    layout: horizontal;
    height: 1fr;
    background: #0d1117;
}

#chat-view {
    width: 1fr;
    height: 1fr;
    overflow-y: auto;
    padding: 1 2;
}

.message {
    width: 100%;
    margin: 0 0 1 0;
}

.message.user {
    color: #58a6ff;
}

.message.assistant {
    color: #e6edf3;
}

.message.tool {
    color: #7ee787;
    border-left: solid #238636;
    background: #10161f;
    padding: 0 1;
}

.message.tool-result {
    color: #9da7b3;
    border-left: solid #6e7681;
    background: #11161d;
    padding: 0 1;
}

.message.error {
    color: #ff7b72;
    border-left: solid #da3633;
    background: #1a1114;
    padding: 0 1;
}

#buddy-panel {
    dock: right;
    width: 18;
    height: 1fr;
    border-left: solid #30363d;
    background: #0f141b;
    align: center middle;
    content-align: center middle;
}

#status-bar {
    height: 1;
    background: #161b22;
    color: #8b949e;
    padding: 0 1;
}

#input-area {
    height: 7;
    border-top: solid #1f6feb;
    background: #0d1117;
    padding: 0 1;
}

#composer {
    width: 100%;
    height: 100%;
    background: #0d1117;
    color: #e6edf3;
    border: none;
}

#input-hint {
    height: 1;
    background: #0d1117;
    color: #8b949e;
    padding: 0 1;
}
"""
