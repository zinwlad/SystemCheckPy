# gui.py
import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QComboBox, QPushButton, QVBoxLayout, QWidget, QTextEdit
from PyQt5.QtGui import QClipboard
from system_checks import run_command
from logger import setup_logger, log_command_result
from admin_check import is_admin
from commands import commands

class SystemCheckApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SystemCheckPy GUI")
        self.setGeometry(100, 100, 600, 400)
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        self.command_dropdown = QComboBox()
        self.command_dropdown.addItems(commands.keys())
        layout.addWidget(QLabel("Выберите команду:"))
        layout.addWidget(self.command_dropdown)

        self.description_label = QLabel("Выберите команду для отображения описания.")
        layout.addWidget(self.description_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        layout.addWidget(QLabel("Результат:"))
        layout.addWidget(self.result_text)

        self.execute_button = QPushButton("Выполнить")
        self.execute_button.clicked.connect(self.execute_command)
        layout.addWidget(self.execute_button)

        self.clear_button = QPushButton("Очистить")
        self.clear_button.clicked.connect(self.result_text.clear)
        layout.addWidget(self.clear_button)

        self.copy_button = QPushButton("Копировать результат")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.copy_button)

        self.exit_button = QPushButton("Выход")
        self.exit_button.clicked.connect(self.close)
        layout.addWidget(self.exit_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.command_dropdown.currentIndexChanged.connect(self.update_description)
        self.update_description()

    def update_description(self):
        selected_command = self.command_dropdown.currentText()
        description = commands[selected_command]["description"]
        self.description_label.setText(description)

    def execute_command(self):
        selected_command = self.command_dropdown.currentText()
        command = commands[selected_command]["command"]
        self.result_text.setPlainText("Выполняется...")
        QApplication.processEvents()  # Обновляем интерфейс
        result = run_command(command)
        log_command_result(selected_command, result)
        self.result_text.setPlainText(f"Команда: {selected_command}\n\n{result}")

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.result_text.toPlainText())

def main():
    setup_logger()
    if not is_admin():
        print("Предупреждение: Для некоторых проверок требуются права администратора.")
    app = QApplication(sys.argv)
    window = SystemCheckApp()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()