import sys
import os
import subprocess
import json
import logging
import time
import re
from datetime import datetime
from typing import Dict, Any, Optional, List, Tuple, Union

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QTextEdit, QLabel, QComboBox, QMessageBox,
    QProgressBar, QSizePolicy, QSplitter, QFrame, QMenuBar, QMenu, QFileDialog, QStatusBar,
    QCheckBox, QLineEdit, QSpinBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QPoint, QSettings
from PyQt6.QtGui import QTextCursor, QAction, QIcon, QFont, QColor, QTextCharFormat, QTextFormat, QPalette, QKeySequence

# Настройка логирования
def setup_logging():
    """Настройка системы логирования"""
    log_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    
    # Файловый обработчик
    file_handler = logging.FileHandler(
        filename='system_check.log',
        mode='w',
        encoding='utf-8'
    )
    file_handler.setFormatter(log_formatter)
    file_handler.setLevel(logging.DEBUG)
    
    # Консольный обработчик
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(log_formatter)
    console_handler.setLevel(logging.INFO)
    
    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Настройка логгера для PyQt
    qt_logger = logging.getLogger('PyQt6')
    qt_logger.setLevel(logging.WARNING)
    
    return root_logger

# Инициализация логирования
logger = setup_logging()

# Импорты ваших модулей
from system_checks import run_command, launch_command, collect_output
from admin_check import is_admin
from commands import commands


logger = logging.getLogger(__name__)

# --- Глобальные настройки ---
DEFAULT_TIMEOUT = 60
LONG_RUNNING_COMMANDS = {"Проверить целостность системных файлов", "Выполнить CHKDSK", "Выполнить DISM"}

# --- Вспомогательная функция для создания иконок ---
def create_icon_from_color(color: QColor) -> QIcon:
    """Создаёт иконку из сплошного цвета."""
    pixmap = QPixmap(16, 16)
    pixmap.fill(color)
    return QIcon(pixmap)

class CommandWorker(QThread):
    finished = pyqtSignal(str, object)  # command_name, result
    progress = pyqtSignal(str, bool)    # text, is_stderr

    def __init__(self, command, command_name, timeout=30):
        super().__init__()
        self.command = command
        self.command_name = command_name
        self.timeout = timeout
        self.process = None
        self._cancelled = False
        self.process = None
        self._start_time = None
        
    def cancel(self):
        """Запрос отмены выполнения команды."""
        self._cancelled = True
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.progress.emit("Отмена выполнения команды...", False)  # False indicates this is not an error message
            except Exception as e:
                logger.error(f"Ошибка при отмене команды: {e}")
                self.progress.emit(f"Ошибка при отмене команды: {e}", True)  # True indicates this is an error message
    
    def run(self):
        """Запускает выполнение команды в отдельном потоке."""
        logger.info(f"Запуск команды: {self.command_name}")
        self._start_time = time.time()
        
        result = {
            "stdout": "",
            "stderr": "",
            "returncode": -1,
            "timeout": False,
            "execution_time": 0
        }
        
        try:
            self.progress.emit(f"Запуск команды: {self.command_name}...", False)
            
            # Запускаем команду
            self.process = launch_command(self.command)
            
            if self._cancelled:
                self._cleanup_process()
                result["stderr"] = "Выполнение отменено пользователем"
                result["returncode"] = -1
            else:
                # Собираем вывод с таймаутом
                result = collect_output(self.process, timeout=self.timeout)
                
                # Логируем результат
                exec_time = time.time() - self._start_time
                result["execution_time"] = round(exec_time, 2)
                
                log_msg = (
                    f"Команда завершена: {self.command_name}\n"
                    f"Код возврата: {result['returncode']}\n"
                    f"Время выполнения: {result['execution_time']} сек"
                )
                
                if result['stderr']:
                    logger.warning(f"{log_msg}\nSTDERR: {result['stderr']}")
                else:
                    logger.info(log_msg)
                    
        except subprocess.TimeoutExpired:
            self._cleanup_process()
            error_msg = f"Превышено время ожидания ({self.timeout} сек)"
            logger.error(f"{self.command_name}: {error_msg}")
            self.progress.emit(error_msg, True)
            result.update({
                "stderr": error_msg,
                "timeout": True,
                "returncode": -2
            })
            
        except Exception as e:
            self._cleanup_process()
            error_msg = f"Ошибка при выполнении команды: {str(e)}"
            logger.error(f"{self.command_name}: {error_msg}", exc_info=True)
            result.update({
                "stderr": error_msg,
                "returncode": -1
            })
            
        finally:
            # Гарантируем, что процесс завершен
            self._cleanup_process()
            
            # Отправляем сигнал о завершении
            self.finished.emit(self.command_name, result)
    
    def _cleanup_process(self):
        """Безопасное завершение процесса и освобождение ресурсов."""
        if self.process:
            try:
                if self.process.poll() is None:
                    # Процесс все еще выполняется, завершаем его
                    self.process.terminate()
                    try:
                        self.process.wait(timeout=5)  # Даем время на корректное завершение
                    except subprocess.TimeoutExpired:
                        self.process.kill()  # Принудительное завершение
                        self.process.wait()
                
                # Закрываем потоки ввода/вывода
                for stream in [self.process.stdout, self.process.stderr]:
                    if stream:
                        try:
                            stream.close()
                        except Exception as e:
                            logger.debug(f"Ошибка при закрытии потока: {e}")
                            
            except Exception as e:
                logger.error(f"Ошибка при завершении процесса: {e}")
            finally:
                self.process = None


class SystemCheckApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("SystemCheckPy")
        
        # Устанавливаем размеры окна
        screen = QApplication.primaryScreen().availableGeometry()
        width = min(1000, screen.width() - 50)
        height = min(700, screen.height() - 100)
        
        # Устанавливаем геометрию и минимальный размер
        self.resize(width, height)
        self.setMinimumSize(800, 600)
        
        # Центрируем окно
        frame_geometry = self.frameGeometry()
        center_point = screen.center()
        frame_geometry.moveCenter(center_point)
        self.move(frame_geometry.topLeft())
        
        # Настройки приложения
        self.settings = QSettings("SystemCheckPy", "SystemCheckPyApp")
        
        # Инициализируем UI
        self.initUI()
        
        # Применяем тему
        self.apply_theme()
        
        # Убедимся, что окно будет видимым
        self.show()
        self.activateWindow()
        self.raise_()
        
        # Принудительно обновляем окно
        QApplication.processEvents()

    def initUI(self):
        # Сначала создаем все виджеты
        self.fav_only_checkbox = QCheckBox("Только избранное")
        
        # Затем настраиваем меню, которое зависит от виджетов
        self.create_menu_bar()
        
        # Центральный виджет
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # --- Панель инструментов ---
        toolbar_layout = QHBoxLayout()

        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText("🔍 Поиск команды...")
        self.search_input.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 3px;")
        toolbar_layout.addWidget(self.search_input)

        toolbar_layout.addWidget(self.fav_only_checkbox)

        main_layout.addLayout(toolbar_layout)

        # --- Разделение на панели ---
        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(5) # Ширина разделителя
        main_layout.addWidget(splitter)

        # Левая панель (команды, описание)
        left_frame = QFrame()
        left_frame.setStyleSheet("QFrame { background-color: #f9f9f9; border-right: 1px solid #ccc; }") # Светлый фон
        left_layout = QVBoxLayout(left_frame)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop) # Выравнивание по верху

        self.command_dropdown = QComboBox()
        self.command_dropdown.setPlaceholderText("Выберите команду...")
        self.command_dropdown.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 3px;")
        left_layout.addWidget(QLabel("Выберите команду:"))
        left_layout.addWidget(self.command_dropdown)

        # Кнопка избранного
        fav_button_layout = QHBoxLayout()
        self.favorite_button = QPushButton("☆ В избранное")
        self.favorite_button.setStyleSheet("QPushButton { padding: 5px; }")
        self.favorite_button.clicked.connect(self.toggle_favorite)
        fav_button_layout.addWidget(self.favorite_button)
        fav_button_layout.addStretch() # Растягиваем, чтобы кнопка была слева
        left_layout.addLayout(fav_button_layout)

        # Описание
        self.description_label = QLabel("Выберите команду для отображения описания.")
        self.description_label.setWordWrap(True) # Перенос текста
        self.description_label.setStyleSheet("QLabel { background-color: #eef5ff; padding: 8px; border-radius: 3px; border: 1px solid #ccc; }") # Светло-голубой фон
        left_layout.addWidget(QLabel("Описание:"))
        left_layout.addWidget(self.description_label)

        # Правая панель (результат)
        right_frame = QFrame()
        right_frame.setStyleSheet("QFrame { background-color: #ffffff; }") # Белый фон
        right_layout = QVBoxLayout(right_frame)

        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        # Моноширинный шрифт и отключение переноса строк
        mono = QFont("Consolas", 10) # Увеличен размер шрифта
        mono.setStyleHint(QFont.StyleHint.Monospace)
        self.result_text.setFont(mono)
        self.result_text.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        self.result_text.setStyleSheet("QTextEdit { border: 1px solid #ccc; }") # Рамка

        right_layout.addWidget(QLabel("Результат:"))
        right_layout.addWidget(self.result_text)

        # Добавляем панели в сплиттер
        splitter.addWidget(left_frame)
        splitter.addWidget(right_frame)
        splitter.setSizes([350, 650]) # Установлены начальные размеры

        # --- Панель управления ---
        controls_frame = QFrame()
        controls_frame.setFrameShape(QFrame.Shape.StyledPanel)
        controls_frame.setStyleSheet("QFrame { background-color: #f0f0f0; padding: 5px; }") # Светло-серый фон
        controls_layout = QHBoxLayout(controls_frame)

        # Таймаут
        timeout_layout = QHBoxLayout()
        timeout_layout.addWidget(QLabel("⏱️ Таймаут (сек):"))
        self.timeout_spin = QSpinBox()
        self.timeout_spin.setRange(5, 36000)
        self.timeout_spin.setValue(DEFAULT_TIMEOUT)
        self.timeout_spin.setStyleSheet("padding: 3px;")
        timeout_layout.addWidget(self.timeout_spin)
        timeout_layout.addStretch() # Растягиваем
        controls_layout.addLayout(timeout_layout)

        # Прогресс
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { text-align: center; }") # Центрирование текста
        controls_layout.addWidget(self.progress_bar)

        # Кнопки
        button_layout = QHBoxLayout()
        self.execute_button = QPushButton("▶️ Выполнить")
        self.execute_button.setStyleSheet("QPushButton { background-color: #4CAF50; color: white; padding: 5px 10px; border-radius: 3px; } QPushButton:hover { background-color: #45a049; }") # Зелёная кнопка
        self.execute_button.clicked.connect(self.execute_command)
        button_layout.addWidget(self.execute_button)

        self.cancel_button = QPushButton("❌ Отмена")
        self.cancel_button.setEnabled(False)
        self.cancel_button.setStyleSheet("QPushButton { background-color: #f44336; color: white; padding: 5px 10px; border-radius: 3px; } QPushButton:hover { background-color: #da190b; }") # Красная кнопка
        self.cancel_button.clicked.connect(self.cancel_command)
        button_layout.addWidget(self.cancel_button)

        self.clear_button = QPushButton("🗑️ Очистить")
        self.clear_button.setStyleSheet("QPushButton { padding: 5px 10px; }")
        self.clear_button.clicked.connect(self.result_text.clear)
        button_layout.addWidget(self.clear_button)

        self.copy_button = QPushButton("📋 Копировать")
        self.copy_button.setStyleSheet("QPushButton { padding: 5px 10px; }")
        self.copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(self.copy_button)

        self.save_button = QPushButton("💾 Сохранить")
        self.save_button.setStyleSheet("QPushButton { padding: 5px 10px; }")
        self.save_button.clicked.connect(self.save_result)
        button_layout.addWidget(self.save_button)

        controls_layout.addLayout(button_layout)

        main_layout.addWidget(controls_frame)

        # --- Нижняя панель ---
        bottom_layout = QHBoxLayout()
        bottom_layout.addStretch()
        self.exit_button = QPushButton("🚪 Выход")
        self.exit_button.setStyleSheet("QPushButton { padding: 5px 10px; }")
        self.exit_button.clicked.connect(self.close)
        bottom_layout.addWidget(self.exit_button)

        main_layout.addLayout(bottom_layout)

        # Статусбар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готово")

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
        self.setup_shortcuts()

        # Восстанавливаем настройки
        saved_timeout = int(self.settings.value("timeout", DEFAULT_TIMEOUT))
        self.timeout_spin.setValue(saved_timeout)

    def create_menu_bar(self):
        """Создаёт меню."""
        menubar = self.menuBar()

        # Меню 'Файл'
        file_menu = menubar.addMenu('Файл')
        save_action = QAction('Сохранить результат', self)
        save_action.setShortcut(QKeySequence.StandardKey.Save)
        save_action.triggered.connect(self.save_result)
        file_menu.addAction(save_action)

        exit_action = QAction('Выход', self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # Меню 'Вид'
        view_menu = menubar.addMenu('Вид')
        toggle_fav_action = QAction('Только избранное', self, checkable=True)
        toggle_fav_action.setChecked(self.fav_only_checkbox.isChecked())
        toggle_fav_action.triggered.connect(lambda: self.fav_only_checkbox.setChecked(not self.fav_only_checkbox.isChecked()))
        view_menu.addAction(toggle_fav_action)

        # Меню 'Помощь'
        help_menu = menubar.addMenu('Помощь')
        about_action = QAction('О программе', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def setup_shortcuts(self):
        """Настраивает горячие клавиши."""
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

    def apply_theme(self):
        """Применяет светлую тему."""
        # PyQt6 использует QPalette для настройки цветов
        palette = QPalette()
        # Можно настроить конкретные цвета, например:
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

    def show_about(self):
        """Показывает окно 'О программе'."""
        QMessageBox.about(self, "О SystemCheckPy", "SystemCheckPy v1.0\n\nУтилита для диагностики системы Windows.")

    def update_description(self):
        selected_command = self.command_dropdown.currentText()
        if selected_command and selected_command in commands:
            description = commands[selected_command]["description"]
            self.description_label.setText(description)
            # Обновляем состояние кнопки избранного
            if selected_command in self.favorites:
                self.favorite_button.setText("★ Удалить из избранного")
                # self.favorite_button.setIcon(create_icon_from_color(QColor("#FFD700"))) # Жёлтая звезда (опционально)
            else:
                self.favorite_button.setText("☆ В избранное")
                # self.favorite_button.setIcon(QIcon()) # Убираем иконку (опционально)
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
                self.execute_button.setEnabled(False)
                return
            try:
                command = meta["template"].format(input=text)
            except (KeyError, ValueError) as e:
                QMessageBox.warning(self, "Ошибка", f"Неверный формат параметра: {e}")
                return
        else:
            # Если нет template, используем стандартную команду
            command = meta["command"]

        try:
            # Настройка интерфейса перед выполнением команды
            self.set_status("Выполняется...")
            
            # Сохраняем текущую позицию прокрутки
            scroll_position = self.result_text.verticalScrollBar().value()
            
            # Очищаем только если это новая команда, а не продолжение вывода
            if not self.result_text.toPlainText():
                self.result_text.clear()
                
            self.append_stream("\n" + "=" * 50 + "\n", False)
            self.append_stream(f"ВЫПОЛНЕНИЕ КОМАНДЫ: {selected_command}\n", False)
            self.append_stream("=" * 50 + "\n\n", False)
            
            # Прокручиваем к началу вывода
            self.result_text.verticalScrollBar().setValue(self.result_text.verticalScrollBar().maximum())
            
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.execute_button.setEnabled(False)
            self.cancel_button.setEnabled(True)

            # Увеличенный таймаут для долгих команд
            user_timeout = int(self.timeout_spin.value())
            timeout = max(user_timeout, 1800) if selected_command in LONG_RUNNING_COMMANDS else user_timeout

            # Создаем и запускаем воркер
            self.worker = CommandWorker(command, selected_command, timeout=timeout)
            self.worker.progress[str, bool].connect(self.on_stream_progress)
            self.worker.finished[str, object].connect(self.on_command_finished)
            self.worker.start()

        except Exception as e:
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
        # result: dict => {'stdout','stderr','returncode','timeout'}
        stdout = result.get("stdout", "")
        stderr = result.get("stderr", "")
        returncode = result.get("returncode", 0)
        success = (returncode == 0)
        
        # Очищаем предыдущий вывод
        self.result_text.clear()
        
        # Добавляем заголовок команды
        self.append_stream(f"ВЫПОЛНЕНИЕ КОМАНДЫ: {command_name}\n", False)
        self.append_stream("=" * 50 + "\n\n", False)
        
        # Выводим результат выполнения
        if success:
            self.append_stream("✅ КОМАНДА УСПЕШНО ВЫПОЛНЕНА\n\n", False)
        else:
            self.append_stream(f"❌ ОШИБКА ВЫПОЛНЕНИЯ (код {returncode})\n\n", True)
        
        # Выводим stdout, если есть
        if stdout and stdout.strip():
            # Удаляем лишние переносы строк в начале и конце
            stdout = stdout.strip('\r\n')
            self.append_stream("ВЫВОД КОМАНДЫ:\n", False)
            self.append_stream("-" * 50 + "\n", False)
            self.append_stream(stdout + "\n\n", False)
        
        # Выводим stderr, если есть
        if stderr and stderr.strip():
            # Удаляем лишние переносы строк в начале и конце
            stderr = stderr.strip('\r\n')
            self.append_stream("ОШИБКИ:\n", True)
            self.append_stream("-" * 50 + "\n", True)
            self.append_stream(stderr + "\n\n", True)
        
        # Добавляем завершающий разделитель
        self.append_stream("=" * 50 + "\n", False)
        
        # Прокручиваем к началу вывода
        cursor = self.result_text.textCursor()
        cursor.movePosition(QTextCursor.MoveOperation.Start)
        self.result_text.setTextCursor(cursor)
        
        # Обновляем интерфейс
        self.progress_bar.setVisible(False)
        self.execute_button.setEnabled(True)
        self.cancel_button.setEnabled(False)
        
        # Обновляем статус
        status_msg = f"Готово: {command_name}" if success else f"Ошибка при выполнении: {command_name}"
        self.set_status(status_msg, is_error=not success)
        
        # Обновляем статус
        status_text = "Готово" if success else f"Ошибка (код {returncode})"
        self.set_status(status_text, is_success=success, is_error=not success)
        
        # Убедимся, что окно видимо и активно
        self.show()
        self.activateWindow()
        self.raise_()
        
        # Выводим в консоль для отладки
        print("\n" + "=" * 50)
        print(f"Команда завершена: {command_name}")
        print(f"Код возврата: {returncode}")
        if stderr:
            print("\nSTDERR:")
            print(stderr)
        if stdout:
            print("\nSTDOUT:")
            print(stdout)
        print("=" * 50 + "\n")

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
                     .replace("<", "<")
                     .replace(">", ">")
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
            # QDesktopServices.openUrl(QUrl.fromLocalFile(logs_dir)) # Альтернатива os.startfile
            os.startfile(logs_dir)
        except Exception as e:
            self.result_text.setPlainText(f"Не удалось открыть папку логов: {e}")
            self.set_status("Ошибка: не удалось открыть логи", is_error=True)

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
        sb = self.status_bar
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


def main():
    # Проверка прав администратора
    if not is_admin():
        print("Предупреждение: Приложение запущено без прав администратора. Некоторые функции могут быть недоступны.")

    try:
        # Создаем приложение
        app = QApplication(sys.argv)
        
        # Создаем и настраиваем главное окно
        window = SystemCheckApp()
        
        # Устанавливаем позицию и размер
        window.move(100, 100)
        window.resize(1000, 700)
        
        # Показываем и активируем окно
        window.show()
        window.activateWindow()
        window.raise_()
        window.setFocus()
        
        # Даем время на инициализацию интерфейса
        for _ in range(3):
            app.processEvents()
            QThread.msleep(100)
        return app.exec()
        
    except Exception as e:
        import traceback
        error_msg = f"Произошла критическая ошибка при запуске приложения:\n{str(e)}\n\nТрассировка:\n{traceback.format_exc()}"
        print(error_msg, file=sys.stderr)
        
        # Пытаемся показать сообщение об ошибке в GUI, если это возможно
        try:
            error_box = QMessageBox()
            error_box.setIcon(QMessageBox.Critical)
            error_box.setWindowTitle("Ошибка запуска")
            error_box.setText("Не удалось запустить приложение")
            error_box.setDetailedText(error_msg)
            error_box.exec()
        except:
            pass
            
        return 1

if __name__ == "__main__":
    # Initialize the application
    app = QApplication(sys.argv)
    
    # Run the main application
    sys.exit(main())