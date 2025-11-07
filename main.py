#main.py
import sys
import os
import re
import ctypes
import logging
from datetime import datetime

# Импорты PyQt6
from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QLabel, QComboBox, QPushButton, QVBoxLayout,
    QWidget, QTextEdit, QProgressBar, QSpinBox, QLineEdit, QCheckBox,
    QMessageBox, QFileDialog, QInputDialog, QHBoxLayout, QSplitter, QFrame
)
from PyQt6.QtGui import (
    QFont, QPalette, QColor, QAction, QKeySequence, QTextCursor, QTextCharFormat
)
from PyQt6.QtCore import (
    QThread, pyqtSignal, QSettings, Qt, QTimer
)

# Импорты ваших модулей
from system_checks import run_command, launch_command, collect_output
from logger import setup_logger, log_command_result
from admin_check import is_admin
from commands import commands


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
            if self.process and self.process.poll() is None:  # Проверяем, что процесс ещё запущен
                # Попробовать завершить процесс корректно
                self.process.terminate()
                try:
                    self.process.wait(timeout=1)  # Ждём завершения до 1 секунды
                except:
                    # Если не завершается, убиваем принудительно
                    self.process.kill()
        except Exception:
            pass

    def run(self):
        result = {"stdout": "", "stderr": "", "returncode": -1, "error": None}
        try:
            # Запускаем команду
            self.process = launch_command(self.command)
            
            # Буферы для сбора вывода
            stdout_chunks = []
            stderr_chunks = []
            
            # Чтение stdout и stderr в реальном времени
            while True:
                # Проверяем, не отменен ли процесс
                if self._cancelled:
                    self.process.terminate()
                    result["stderr"] = "Команда отменена пользователем.\n"
                    break
                    
                # Проверяем, завершился ли процесс
                return_code = self.process.poll()
                if return_code is not None:
                    # Процесс завершился, дочитываем оставшийся вывод
                    for line in self.process.stdout:
                        try:
                            text = line.decode('utf-8', errors='replace')
                        except Exception:
                            text = line.decode(errors='replace')
                        stdout_chunks.append(text)
                        self.progress.emit(text, False)
                        
                    for line in self.process.stderr:
                        try:
                            text = line.decode('utf-8', errors='replace')
                        except Exception:
                            text = line.decode(errors='replace')
                        stderr_chunks.append(text)
                        self.progress.emit(text, True)
                    
                    result.update({
                        "stdout": "".join(stdout_chunks),
                        "stderr": "".join(stderr_chunks),
                        "returncode": return_code
                    })
                    break
                    
                # Чтение вывода, если он есть
                for stream, chunks, is_error in [
                    (self.process.stdout, stdout_chunks, False),
                    (self.process.stderr, stderr_chunks, True)
                ]:
                    if stream is None:
                        continue
                    for line in iter(stream.readline, b''):
                        try:
                            text = line.decode('utf-8', errors='replace')
                        except Exception:
                            text = line.decode(errors='replace')
                        chunks.append(text)
                        self.progress.emit(text, is_error)
                        
            # Если процесс все еще выполняется, завершаем его
            if self.process.poll() is None:
                try:
                    self.process.terminate()
                    self.process.wait(timeout=2)
                except:
                    try:
                        self.process.kill()
                    except:
                        pass
                        
        except Exception as e:
            error_msg = str(e)
            result.update({
                "error": error_msg,
                "stderr": f"Ошибка при выполнении команды: {error_msg}"
            })
            
        # Если команда была отменена, обновляем сообщение об ошибке
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
        self.setGeometry(100, 100, 800, 600)
        # Настройки приложения
        self.settings = QSettings("SystemCheckPy", "SystemCheckPyApp")
        self.initUI()
        self.apply_theme()

    def initUI(self):
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Панель инструментов ---
        toolbar_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск команды...")
        self.search_input.textChanged.connect(self.refresh_command_list)
        toolbar_layout.addWidget(self.search_input)

        self.fav_only_checkbox = QCheckBox("★ Только избранное")
        self.fav_only_checkbox.stateChanged.connect(self.refresh_command_list)
        toolbar_layout.addWidget(self.fav_only_checkbox)

        main_layout.addLayout(toolbar_layout)

        # --- Разделение на панели ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        main_layout.addWidget(splitter)

        # Левая панель (команды, описание)
        left_frame = QFrame()
        left_layout = QVBoxLayout(left_frame)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Выравнивание по верху

        self.command_dropdown = QComboBox()
        self.command_dropdown.setPlaceholderText("Выберите команду...")
        left_layout.addWidget(QLabel("Выберите команду:"))
        left_layout.addWidget(self.command_dropdown)

        # Кнопка избранного
        fav_button_layout = QHBoxLayout()
        self.favorite_button = QPushButton("☆ В избранное")
        self.favorite_button.clicked.connect(self.toggle_favorite)
        fav_button_layout.addWidget(self.favorite_button)
        fav_button_layout.addStretch() # Растягиваем, чтобы кнопка была слева
        left_layout.addLayout(fav_button_layout)

        # Описание
        self.description_label = QLabel("Выберите команду для отображения описания.")
        self.description_label.setWordWrap(True) # Перенос текста
        self.description_label.setStyleSheet("QLabel { background-color: #f0f0f0; padding: 5px; border-radius: 3px; }")
        left_layout.addWidget(QLabel("Описание:"))
        left_layout.addWidget(self.description_label)

        # Правая панель (результат)
        right_frame = QFrame()
        right_layout = QVBoxLayout(right_frame)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        # Моноширинный шрифт и отключение переноса строк
        mono = QFont("Consolas", 9)
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.result_text.setFont(mono)
        self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)

        right_layout.addWidget(QLabel("Результат:"))
        right_layout.addWidget(self.result_text)

        # Добавляем панели в сплиттер
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([300, 500]) # Устанавливаем начальные размеры

        # --- Панель управления ---
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_layout = QHBoxLayout(controls_frame)

        # Таймаут
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("⏱️ Таймаут (сек):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 36000)
        self.timeout_spin.setValue(60)
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch() # Растягиваем
        controls_layout.addLayout(timeout_layout)

        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        controls_layout.addWidget(self.progress_bar)

        # Кнопки
        button_layout = QHBoxLayout()
        self.execute_button = QPushButton("▶️ Выполнить")
        self.execute_button.clicked.connect(self.execute_command)
        button_layout.addWidget(self.execute_button)

        self.cancel_button = QPushButton("❌ Отмена")
        self.cancel_button.setEnabled(False)
        self.cancel_button.clicked.connect(self.cancel_command)
        button_layout.addWidget(self.cancel_button)

        self.clear_button = QPushButton("🗑️ Очистить")
        self.clear_button.clicked.connect(self.result_text.clear)
        button_layout.addWidget(self.clear_button)

        self.copy_button = QPushButton("📋 Копировать")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(self.copy_button)

        self.save_button = QPushButton("💾 Сохранить")
        self.save_button.clicked.connect(self.save_result)
        button_layout.addWidget(self.save_button)

        controls_layout.addLayout(button_layout)

        main_layout.addWidget(controls_frame)

        # --- Нижняя панель ---
        bottom_layout = QHBoxLayout()
        self.view_log_button = QPushButton("📄 Просмотр лога")
        self.view_log_button.clicked.connect(self.view_log)
        bottom_layout.addWidget(self.view_log_button)

        self.open_logs_button = QPushButton("📂 Открыть папку логов")
        self.open_logs_button.clicked.connect(self.open_logs_folder)
        bottom_layout.addWidget(self.open_logs_button)

        self.exit_button = QPushButton("🚪 Выход")
        self.exit_button.clicked.connect(self.close)
        bottom_layout.addWidget(self.exit_button)

        main_layout.addLayout(bottom_layout)

        # Статусбар
        self.statusBar().showMessage("Готово")

        # Инициализация списка команд и избранного
        self.all_commands = list(commands.keys())
        # QSettings может вернуть строку; нормализуем к списку
        fav_list = self.settings.value("favorites", [])
        if isinstance(fav_list, str):
            fav_list = [x for x in fav_list.split("||") if x]
        self.favorites = set(fav_list)

        self.command_dropdown.currentTextChanged.connect(self.update_description) # PyQt6: currentTextChanged
        self.refresh_command_list()

        # Горячие клавиши
        # PyQt6: QShortcut теперь принимает QKeySequence в конструкторе
        execute_shortcut = QAction("Execute", self)
        execute_shortcut.setShortcut(QKeySequence.StandardKey.InsertParagraphSeparator) # Ctrl+Enter не работает как StandardKey, используем InsertParagraphSeparator или кастомный
        execute_shortcut.triggered.connect(self.execute_command)
        self.addAction(execute_shortcut)

        search_shortcut = QAction("Focus Search", self)
        search_shortcut.setShortcut(QKeySequence.StandardKey.Find)
        search_shortcut.triggered.connect(self.search_input.setFocus)
        self.addAction(search_shortcut)

        fav_shortcut = QAction("Toggle Favorite", self)
        fav_shortcut.setShortcut(QKeySequence.StandardKey.AddTab) # Ctrl+T, можно изменить
        fav_shortcut.triggered.connect(self.toggle_favorite)
        self.addAction(fav_shortcut)

        logs_shortcut = QAction("Open Logs Folder", self)
        logs_shortcut.setShortcut(QKeySequence.StandardKey.Open)
        logs_shortcut.triggered.connect(self.open_logs_folder)
        self.addAction(logs_shortcut)

        cancel_shortcut = QAction("Cancel", self)
        cancel_shortcut.setShortcut(QKeySequence.StandardKey.Cancel)
        cancel_shortcut.triggered.connect(self.cancel_command)
        self.addAction(cancel_shortcut)

        # Восстанавливаем настройки
        saved_timeout = int(self.settings.value("timeout", 60))
        self.timeout_spin.setValue(saved_timeout)

    def apply_theme(self):
        """Применяет светлую тему."""
        # PyQt6 использует QPalette для настройки цветов
        palette = QPalette()
        # palette.setColor(QPalette.ColorRole.Window, QColor(240, 240, 240))
        # palette.setColor(QPalette.ColorRole.WindowText, QColor(0, 0, 0))
        # palette.setColor(QPalette.ColorRole.Base, QColor(255, 255, 255))
        # palette.setColor(QPalette.ColorRole.AlternateBase, QColor(245, 245, 245))
        # palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(255, 255, 220))
        # palette.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 0, 0))
        # palette.setColor(QPalette.ColorRole.Text, QColor(0, 0, 0))
        # palette.setColor(QPalette.ColorRole.Button, QColor(240, 240, 240))
        # palette.setColor(QPalette.ColorRole.ButtonText, QColor(0, 0, 0))
        # palette.setColor(QPalette.ColorRole.BrightText, QColor(255, 0, 0))
        # palette.setColor(QPalette.ColorRole.Link, QColor(0, 0, 255))
        # palette.setColor(QPalette.ColorRole.Highlight, QColor(51, 153, 255))
        # palette.setColor(QPalette.ColorRole.HighlightedText, QColor(255, 255, 255))
        self.setPalette(palette)

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
        logger = logging.getLogger(__name__)

        if not selected_command:
            logger.warning("Попытка выполнения пустой команды")
            return

        meta = commands.get(selected_command, {})
        logger.debug(f"Метаданные команды {selected_command}: {meta}")

        # Проверка прав администратора для команды
        if meta.get("requires_admin") and not is_admin():
            reply = QMessageBox.question(
                self,
                "Требуются права администратора",
                "Команда требует прав администратора. Перезапустить приложение с повышенными правами?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.Yes,
            )
            if reply == QMessageBox.StandardButton.Yes:
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
                        self.set_status("Ввод не соответствует формату." + hint, is_error=True)
                        return
                except re.error:
                    # Если шаблон неисправен, пропускаем проверку
                    pass

            # Получаем команду для выполнения
            command = meta["template"].format(input=user_input)
        else:
            command = meta["command"]

        # Настройка интерфейса перед выполнением команды
        self.set_status("Выполняется...")
        self.result_text.clear()
        self.append_stream("Выполняется...\n", False)
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, 0)
        self.execute_button.setEnabled(False)
        self.cancel_button.setEnabled(True)
        # УБРАНО: QApplication.processEvents() перед запуском потока

        # Увеличенный таймаут для долгих команд
        LONG = {"Проверить целостность системных файлов", "Выполнить CHKDSK", "Выполнить DISM"}
        user_timeout = int(self.timeout_spin.value())
        timeout = max(user_timeout, 1800) if selected_command in LONG else user_timeout

        try:
            self.worker = CommandWorker(command, selected_command, timeout=timeout)
            self.worker.progress.connect(self.on_stream_progress)
            self.worker.finished.connect(self.on_command_finished)
            self.worker.start() # Запускаем поток ПОСЛЕ настройки интерфейса
        except Exception as e:
            error_msg = f"Ошибка при запуске команды: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.set_status("Ошибка при запуске команды", is_error=True)
            self.result_text.append(error_msg)
            self.progress_bar.setVisible(False)
            self.execute_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            # QMessageBox.critical(self, "Ошибка повышения прав", f"Не удалось перезапустить с правами администратора:\n{e}") # УБРАНО: лишний вызов
            # QApplication.quit() # УБРАНО: лишний quit

    def _start_command_worker(self, command, command_name, timeout):
        """Запускает выполнение команды в отдельном потоке."""
        try:
            self.worker = CommandWorker(command, command_name, timeout=timeout)
            self.worker.progress.connect(self.on_stream_progress)
            self.worker.finished.connect(self.on_command_finished)
            self.worker.start()
        except Exception as e:
            error_msg = f"Ошибка при запуске команды: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.set_status("Ошибка при запуске команды", is_error=True)
            self.result_text.append(error_msg)
            self.progress_bar.setVisible(False)
            self.execute_button.setEnabled(True)
            self.cancel_button.setEnabled(False)
            QMessageBox.critical(self, "Ошибка выполнения", f"Не удалось выполнить команду:\n{e}")

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
        logger = logging.getLogger(__name__)
        logger.debug(f"Завершено выполнение команды: {command_name}")

        # result: dict => {'stdout','stderr','returncode','timeout'}
        stdout = result.get("stdout", "") if isinstance(result, dict) else str(result)
        stderr = result.get("stderr", "") if isinstance(result, dict) else ""
        returncode = result.get("returncode", 0) if isinstance(result, dict) else (0 if stdout and not stdout.startswith("Ошибка") else 1)
        success = (returncode == 0)

        logger.debug(f"Результат выполнения: success={success}, returncode={returncode}")
        logger.debug(f"STDOUT: {stdout[:200]}..." if len(stdout) > 200 else f"STDOUT: {stdout}")
        if stderr:
            logger.warning(f"STDERR: {stderr}")

        # Финальный вывод: сначала stdout, потом stderr
        self.result_text.clear() # Очищаем перед финальным выводом
        if stdout:
            self.result_text.append(stdout.rstrip()) # append добавляет новую строку
        if stderr:
            # Добавим stderr в конец, выделив цветом с помощью HTML
            self.append_stderr_to_result(stderr.rstrip())

        log_command_result(command_name, stdout if success else stderr, success=success)
        self.progress_bar.setVisible(False)
        self.execute_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        if success:
            self.set_status("Готово: выполнено успешно", is_success=True)
        else:
            self.set_status(f"Ошибка выполнения (код {returncode})", is_error=True)

    def on_stream_progress(self, text, is_stderr):
        self.append_stream(text, is_stderr)

    def append_stream(self, text, is_stderr=False):
        """Добавляет текст в QTextEdit с поддержкой цветного вывода stderr."""
        if not text:
            return

        # Нормализуем концы строк
        normalized = text.replace("\r\n", "\n").replace("\r", "\n")
        
        # Убираем лишние пустые строки в конце
        while normalized.endswith("\n"):
            normalized = normalized[:-1]
            
        if not normalized:  # Если после удаления пустых строк ничего не осталось
            return
            
        # Для stdout и stderr используем разные форматы
        cursor = self.result_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.End)
        
        if is_stderr:
            # Для stderr используем красный цвет
            cursor.insertHtml(f'<span style="color:red">{self.escape_html(normalized)}</span><br>')
        else:
            # Для обычного вывода
            cursor.insertText(normalized + "\n")
            
        # Прокрутка вниз
        self.result_text.setTextCursor(cursor)
        self.result_text.ensureCursorVisible()

    def append_stderr_to_result(self, text):
        """Добавляет текст ошибки в результат (устаревший метод, оставлен для совместимости)."""
        self.append_stream(text, is_stderr=True)

    @staticmethod
    def escape_html(s):
        if not s:
            return ""
        return (str(s).replace("&", "&amp;")
                     .replace("<", "&lt;")
                     .replace(">", "&gt;")
                     .replace("\n", "<br>"))

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

    def closeEvent(self, event):
        # Сохраняем таймаут и избранное при выходе
        try:
            self.settings.setValue("timeout", int(self.timeout_spin.value()))
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
        sb = self.statusBar()
        try:
            if is_error:
                sb.setStyleSheet("QStatusBar { color: #d32f2f; }") # Красный цвет
            elif is_success:
                sb.setStyleSheet("QStatusBar { color: #2e7d32; }") # Зелёный цвет
            else:
                sb.setStyleSheet("") # Сброс стиля
            sb.showMessage(message, 5000)
        except Exception:
            pass


if __name__ == "__main__":
    # Настройка логирования
    logger = setup_logger()
    
    # Проверка прав администратора
    if not is_admin():
        logger.warning("Приложение запущено без прав администратора. Некоторые функции могут быть недоступны.")
        print("Предупреждение: Для некоторых проверок требуются права администратора.")
    
    try:
        logger.info("Запуск приложения SystemCheckPy")
        app = QApplication(sys.argv)
        window = SystemCheckApp()
        window.show()
        logger.info("Главное окно отображено")
        sys.exit(app.exec())
    except Exception as e:
        logger.critical(f"Критическая ошибка при запуске приложения: {e}", exc_info=True)
        QMessageBox.critical(None, "Ошибка", f"Произошла критическая ошибка:\n{str(e)}\n\nПроверьте логи для подробностей.")
        sys.exit(1)