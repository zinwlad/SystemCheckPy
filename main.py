# main.py
import sys
import os
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QComboBox, QPushButton, QVBoxLayout, QWidget, QTextEdit, QProgressBar, QSpinBox, QLineEdit, QCheckBox, QMessageBox, QFileDialog, QInputDialog
from PyQt5.QtGui import QFont
from PyQt5.QtCore import QThread, pyqtSignal, QSettings
from PyQt5.QtWidgets import QShortcut
from PyQt5.QtGui import QKeySequence
import re
 
import ctypes
from system_checks import run_command, launch_command, collect_output
from logger import setup_logger, log_command_result
from admin_check import is_admin
from commands import commands
from datetime import datetime

class CommandWorker(QThread):
    finished = pyqtSignal(str, object)
    progress = pyqtSignal(str, bool)  # text, is_stderr

    def __init__(self, command, command_name, timeout=30):
        super().__init__()
        self.command = command
        self.command_name = command_name
        self.timeout = timeout
        self.process = None
        self._cancelled = False

    def cancel(self):
        self._cancelled = True
        try:
            if self.process:
                self.process.kill()
        except Exception:
            pass

    def run(self):
        # Потоковый вывод
        self.process = launch_command(self.command)
        try:
            # Чтение stdout построчно
            if self.process.stdout is not None:
                while True:
                    line = self.process.stdout.readline()
                    if not line:
                        break
                    try:
                        text = line.decode('cp1251', errors='replace')
                    except Exception:
                        text = line.decode(errors='replace')
                    self.progress.emit(text, False)
            # После завершения stdout дочитываем stderr
            if self.process.stderr is not None:
                while True:
                    err = self.process.stderr.readline()
                    if not err:
                        break
                    try:
                        etext = err.decode('cp1251', errors='replace')
                    except Exception:
                        etext = err.decode(errors='replace')
                    self.progress.emit(etext, True)
        except Exception:
            pass
        # Собираем итог
        result = collect_output(self.process, timeout=self.timeout)
        if self._cancelled and result.get("returncode", 0) != 0:
            result["stderr"] = (result.get("stderr") or "").strip()
            if result["stderr"]:
                result["stderr"] = f"Отменено пользователем.\n{result['stderr']}"
            else:
                result["stderr"] = "Отменено пользователем."
        self.finished.emit(self.command_name, result)

class SystemCheckApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SystemCheckPy")
        self.setGeometry(100, 100, 600, 400)
        # Настройки приложения
        self.settings = QSettings("SystemCheckPy", "SystemCheckPyApp")
        self.initUI()

    def initUI(self):
        layout = QVBoxLayout()

        # Поиск и избранное
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("Поиск команды...")
        self.search_input.textChanged.connect(self.refresh_command_list)
        layout.addWidget(self.search_input)

        self.fav_only_checkbox = QCheckBox("Показывать только избранные")
        self.fav_only_checkbox.stateChanged.connect(self.refresh_command_list)
        layout.addWidget(self.fav_only_checkbox)

        self.command_dropdown = QComboBox()
        layout.addWidget(QLabel("Выберите команду:"))
        layout.addWidget(self.command_dropdown)

        self.favorite_button = QPushButton("★ В избранное")
        self.favorite_button.clicked.connect(self.toggle_favorite)
        layout.addWidget(self.favorite_button)

        self.description_label = QLabel("Выберите команду для отображения описания.")
        layout.addWidget(self.description_label)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        # Моноширинный шрифт и перенос
        mono = QFont("Consolas")
        mono.setStyleHint(QFont.Monospace)
        self.result_text.setFont(mono)
        self.result_text.setLineWrapMode(QTextEdit.NoWrap)
        layout.addWidget(QLabel("Результат:"))
        layout.addWidget(self.result_text)

        # Настройка таймаута выполнения команды
        timeout_row_label = QLabel("Таймаут (сек):")
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 36000)
        self.timeout_spin.setValue(60)
        layout.addWidget(timeout_row_label)
        layout.addWidget(self.timeout_spin)

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.execute_button = QPushButton("Выполнить")
        self.execute_button.clicked.connect(self.execute_command)
        layout.addWidget(self.execute_button)

        self.cancel_button = QPushButton("Отмена")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_command)
        layout.addWidget(self.cancel_button)

        self.clear_button = QPushButton("Очистить")
        self.clear_button.clicked.connect(self.result_text.clear)
        layout.addWidget(self.clear_button)

        self.copy_button = QPushButton("Копировать результат")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        layout.addWidget(self.copy_button)

        self.save_button = QPushButton("Сохранить результат")
        self.save_button.clicked.connect(self.save_result)
        layout.addWidget(self.save_button)

        self.view_log_button = QPushButton("Просмотреть лог")
        self.view_log_button.clicked.connect(self.view_log)
        layout.addWidget(self.view_log_button)

        self.open_logs_button = QPushButton("Открыть папку логов")
        self.open_logs_button.clicked.connect(self.open_logs_folder)
        layout.addWidget(self.open_logs_button)

        self.exit_button = QPushButton("Выход")
        self.exit_button.clicked.connect(self.close)
        layout.addWidget(self.exit_button)

        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

        self.statusBar = self.statusBar()
        self.set_status("Готово")

        # Инициализация списка команд и избранного
        self.all_commands = list(commands.keys())
        fav_list = self.settings.value("favorites", [])
        # QSettings может вернуть строку; нормализуем к списку
        if isinstance(fav_list, str):
            fav_list = [x for x in fav_list.split("||") if x]
        self.favorites = set(fav_list)

        self.command_dropdown.currentIndexChanged.connect(self.update_description)
        self.refresh_command_list()

        # Горячие клавиши
        QShortcut(QKeySequence("Ctrl+Enter"), self, activated=self.execute_command)
        QShortcut(QKeySequence("Ctrl+F"), self, activated=self.search_input.setFocus)
        QShortcut(QKeySequence("Ctrl+D"), self, activated=self.toggle_favorite)
        QShortcut(QKeySequence("Ctrl+L"), self, activated=self.open_logs_folder)
        QShortcut(QKeySequence("Esc"), self, activated=self.cancel_command)
        # Темная тема отключена, горячая клавиша убрана

        # Восстанавливаем настройки
        saved_timeout = int(self.settings.value("timeout", 60))
        self.timeout_spin.setValue(saved_timeout)
        # Тема по умолчанию (светлая). Темная тема отключена.

    def update_description(self):
        selected_command = self.command_dropdown.currentText()
        if selected_command and selected_command in commands:
            description = commands[selected_command]["description"]
            self.description_label.setText(description)
            # Обновляем состояние кнопки избранного
            if selected_command in self.favorites:
                self.favorite_button.setText("★ Удалить из избранного")
            else:
                self.favorite_button.setText("☆ В избранное")
            self.execute_button.setEnabled(True)
        else:
            self.description_label.setText("Команда не выбрана или не найдена.")
            self.favorite_button.setText("☆ В избранное")
            self.execute_button.setEnabled(False)

    def execute_command(self):
        selected_command = self.command_dropdown.currentText()
        if not selected_command:
            return
        meta = commands.get(selected_command, {})
        # Проверка прав администратора для команды
        if meta.get("requires_admin") and not is_admin():
            reply = QMessageBox.question(
                self,
                "Требуются права администратора",
                "Команда требует прав администратора. Перезапустить приложение с повышенными правами?",
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.Yes,
            )
            if reply == QMessageBox.Yes:
                self.elevate_and_restart()
            else:
                self.set_status("Отмена: требуются права администратора", is_error=True)
            return

        # Поддержка параметризированных команд через 'template' и 'input_prompt'
        if "template" in meta:
            prompt = meta.get("input_prompt", "Введите значение")
            text, ok = QInputDialog.getText(self, "Параметр команды", prompt)
            if not ok or not text.strip():
                self.set_status("Отменено пользователем", is_error=True)
                return
            user_input = text.strip()
            # Базовая проверка недопустимых символов для безопасности
            disallowed = set(";|&><`$\n\r\t\0")
            if any(ch in disallowed for ch in user_input):
                self.set_status("Недопустимые символы во вводе", is_error=True)
                return
            # Проверка по шаблону, если задан
            pattern = meta.get("input_pattern")
            if pattern:
                try:
                    if re.fullmatch(pattern, user_input) is None:
                        example = meta.get("input_example", "")
                        hint = f" Пример: {example}" if example else ""
                        self.set_status("Ввод не соответствует ожидаемому формату." + hint, is_error=True)
                        return
                except re.error:
                    # Если шаблон неисправен, пропускаем проверку по нему
                    pass
            command = meta["template"].format(input=user_input)
        else:
            command = meta["command"]
        self.set_status("Выполняется...")
        self.result_text.clear()
        self.append_stream("Выполняется...\n", False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.execute_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        QApplication.processEvents()

        # Увеличенный таймаут для долгих команд
        LONG = {"Проверить целостность системных файлов", "Выполнить CHKDSK", "Выполнить DISM"}
        user_timeout = int(self.timeout_spin.value())
        timeout = max(user_timeout, 1800) if selected_command in LONG else user_timeout
        self.worker = CommandWorker(command, selected_command, timeout=timeout)
        self.worker.progress.connect(self.on_stream_progress)
        self.worker.finished.connect(self.on_command_finished)
        self.worker.start()

    def elevate_and_restart(self):
        try:
            script = os.path.abspath(sys.argv[0])
            params = f'"{script}"'
            if len(sys.argv) > 1:
                params += " " + " ".join(f'"{a}"' for a in sys.argv[1:])
            # Запуск с правами администратора
            rc = ctypes.windll.shell32.ShellExecuteW(None, "runas", sys.executable, params, None, 1)
            if rc <= 32:
                raise RuntimeError(f"ShellExecuteW failed with code {rc}")
        except Exception as e:
            QMessageBox.critical(self, "Ошибка повышения прав", f"Не удалось перезапустить с правами администратора:\n{e}")
            return
        # Закрываем текущее приложение, новый экземпляр стартует с UAC
        QApplication.quit()

    def refresh_command_list(self):
        """Фильтрует список команд по поиску и флагу избранного."""
        filter_text = (self.search_input.text() or "").lower()
        fav_only = self.fav_only_checkbox.isChecked()
        # Фильтрация по имени и описанию
        filtered = []
        for name in self.all_commands:
            if fav_only and name not in self.favorites:
                continue
            descr = commands.get(name, {}).get("description", "").lower()
            if filter_text in name.lower() or filter_text in descr:
                filtered.append(name)

        # Обновляем выпадающий список
        self.command_dropdown.blockSignals(True)
        self.command_dropdown.clear()
        if filtered:
            self.command_dropdown.addItems(filtered)
        self.command_dropdown.blockSignals(False)

        # Обновляем описание и кнопку
        self.update_description()

    def toggle_favorite(self):
        name = self.command_dropdown.currentText()
        if not name:
            return
        if name in self.favorites:
            self.favorites.remove(name)
        else:
            self.favorites.add(name)
        # Сохраняем избранные
        fav_serialized = "||".join(sorted(self.favorites))
        self.settings.setValue("favorites", fav_serialized)
        # Если включен фильтр «только избранные», перечитываем список
        if self.fav_only_checkbox.isChecked():
            self.refresh_command_list()
        else:
            # Обновляем только кнопку
            self.update_description()

    def on_command_finished(self, command_name, result):
        # result: dict => {'stdout','stderr','returncode','timeout'}
        stdout = result.get("stdout", "") if isinstance(result, dict) else str(result)
        stderr = result.get("stderr", "") if isinstance(result, dict) else ""
        returncode = result.get("returncode", 0) if isinstance(result, dict) else (0 if stdout and not stdout.startswith("Ошибка") else 1)
        success = (returncode == 0)

        # Финальный вывод: гарантированно показываем результат stdout как есть
        if stdout:
            self.result_text.setPlainText(stdout)
        if stderr:
            # Добавим stderr в конец, выделив цветом
            self.append_stream("\n" + stderr + "\n", True)

        log_command_result(command_name, stdout if success else stderr, success=success)
        self.progress_bar.setVisible(False)
        self.execute_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        self.progress_bar.setVisible(False)
        if success:
            self.set_status("Готово: выполнено успешно", is_success=True)
        else:
            self.set_status(f"Ошибка выполнения (код {returncode})", is_error=True)

    def on_stream_progress(self, text, is_stderr):
        self.append_stream(text, is_stderr)

    def append_stream(self, text, is_stderr):
        # Добавляем поток в QTextEdit
        # Нормализуем окончания строк (CRLF/CR -> LF) и гарантируем завершающий перевод строки
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        if not normalized.endswith("\n"):
            normalized += "\n"
        self.result_text.moveCursor(self.result_text.textCursor().End)
        if is_stderr:
            # Для stderr используем HTML с <br> и цветом
            html = self.escape_html(normalized).replace("\n", "<br>")
            self.result_text.insertHtml(f"<span style='color:#ff5555'>{html}</span>")
        else:
            # Для stdout добавляем как обычный текст — надёжно сохраняет переводы строк
            self.result_text.insertPlainText(normalized)
        self.result_text.moveCursor(self.result_text.textCursor().End)

    @staticmethod
    def escape_html(s):
        return (s.replace("&", "&amp;")
                 .replace("<", "&lt;")
                 .replace(">", "&gt;"))

    def cancel_command(self):
        if hasattr(self, 'worker') and self.worker and self.worker.isRunning():
            self.worker.cancel()
            self.set_status("Отмена выполнения...", is_error=True)

    def copy_to_clipboard(self):
        clipboard = QApplication.clipboard()
        clipboard.setText(self.result_text.toPlainText())

    def view_log(self):
        log_filename = datetime.now().strftime("log_%Y%m%d.txt")
        logs_dir = os.path.join(os.getcwd(), 'logs')
        log_path = os.path.join(logs_dir, log_filename)
        try:
            # Пробуем открыть файл с разными кодировками
            encodings = ['utf-8', 'cp1251', 'cp866']
            content = None
            for encoding in encodings:
                try:
                    with open(log_path, 'r', encoding=encoding) as log_file:
                        content = log_file.read()
                    break
                except UnicodeDecodeError:
                    continue
            if content is not None:
                self.result_text.setPlainText(content)
                self.set_status("Лог загружен")
            else:
                self.result_text.setPlainText("Не удалось прочитать лог-файл из-за проблем с кодировкой.")
                self.set_status("Ошибка: проблема с кодировкой", is_error=True)
        except FileNotFoundError:
            self.result_text.setPlainText("Лог-файл не найден.")
            self.set_status("Ошибка: лог не найден", is_error=True)

    def open_logs_folder(self):
        logs_dir = os.path.join(os.getcwd(), 'logs')
        try:
            if not os.path.isdir(logs_dir):
                os.makedirs(logs_dir, exist_ok=True)
            os.startfile(logs_dir)
        except Exception as e:
            self.result_text.setPlainText(f"Не удалось открыть папку логов: {e}")
            self.set_status("Ошибка: не удалось открыть логи", is_error=True)

    # Темная тема удалена

    def closeEvent(self, event):
        # Сохраняем таймаут и тему при выходе
        try:
            self.settings.setValue("timeout", int(self.timeout_spin.value()))
            # Темная тема удалена — ничего не сохраняем
            fav_serialized = "||".join(sorted(self.favorites))
            self.settings.setValue("favorites", fav_serialized)
        except Exception:
            pass
        super().closeEvent(event)

    def save_result(self):
        try:
            default_dir = self.settings.value("last_save_dir", os.getcwd())
            path, _ = QFileDialog.getSaveFileName(self, "Сохранить результат", os.path.join(default_dir, "result.txt"), "Text Files (*.txt);;HTML Files (*.html)")
            if not path:
                return
            # Определяем формат по расширению
            if path.lower().endswith(".html"):
                content = self.result_text.toHtml()
                mode = "html"
            else:
                content = self.result_text.toPlainText()
                mode = "txt"
                if not path.lower().endswith(".txt"):
                    path += ".txt"
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            self.settings.setValue("last_save_dir", os.path.dirname(path))
            self.set_status(f"Сохранено: {path}")
        except Exception as e:
            self.set_status(f"Ошибка сохранения: {e}", is_error=True)

    def set_status(self, message, is_error=False, is_success=False):
        try:
            if is_error:
                self.statusBar.setStyleSheet("color: #d32f2f;")
            elif is_success:
                self.statusBar.setStyleSheet("color: #2e7d32;")
            else:
                self.statusBar.setStyleSheet("")
            self.statusBar.showMessage(message, 5000)
        except Exception:
            pass

if __name__ == "__main__":
    setup_logger()
    if not is_admin():
        print("Предупреждение: Для некоторых проверок требуются права администратора.")
    app = QApplication(sys.argv)
    window = SystemCheckApp()
    window.show()
    sys.exit(app.exec_())