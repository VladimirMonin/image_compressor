"""
CSS стили для GUI компрессора изображений.
"""

# Стили для кнопок
BUTTON_STYLES = {
    "start": """
        QPushButton {
            background-color: #27ae60;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #2ecc71;
        }
        QPushButton:disabled {
            background-color: #bdc3c7;
        }
    """,
    "stop": """
        QPushButton {
            background-color: #e74c3c;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #c0392b;
        }
        QPushButton:disabled {
            background-color: #bdc3c7;
        }
    """,
    "clear": """
        QPushButton {
            background-color: #f39c12;
            color: white;
            border: none;
            padding: 10px 20px;
            border-radius: 5px;
            font-weight: bold;
        }
        QPushButton:hover {
            background-color: #e67e22;
        }
        QPushButton:disabled {
            background-color: #bdc3c7;
        }
    """,
}

# Стили для DropZone
DROPZONE_STYLES = {
    "normal": """
        QFrame {
            border: 2px dashed #cccccc;
            border-radius: 10px;
            background-color: #f9f9f9;
        }
        QFrame:hover {
            border-color: #0078d4;
            background-color: #f0f8ff;
        }
    """,
    "active": """
        QFrame {
            border: 2px dashed #0078d4;
            border-radius: 10px;
            background-color: #e6f3ff;
        }
    """,
}

# Стили для других элементов
PROGRESS_BAR_STYLE = """
    QProgressBar {
        border: 2px solid #bdc3c7;
        border-radius: 5px;
        text-align: center;
    }
    QProgressBar::chunk {
        background-color: #3498db;
        border-radius: 3px;
    }
"""

LOG_TEXT_STYLE = """
    QTextEdit {
        background-color: #2c3e50;
        color: #ecf0f1;
        border: 1px solid #34495e;
        border-radius: 5px;
        padding: 5px;
        font-family: 'Consolas', 'Monaco', monospace;
    }
"""

TITLE_STYLE = "color: #2c3e50; margin: 10px;"

QUALITY_LABEL_STYLE = "font-weight: bold; color: #2c3e50;"

DROPZONE_LABEL_STYLE = "color: #666666; border: none; background: transparent;"
