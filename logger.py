# logger.py
import logging
import os
from datetime import datetime
from logging.handlers import TimedRotatingFileHandler

def setup_logger():
    # Папка для логов
    logs_dir = os.path.join(os.getcwd(), 'logs')
    os.makedirs(logs_dir, exist_ok=True)

    # Имя файла с датой
    log_filename = datetime.now().strftime("log_%Y%m%d.txt")
    log_path = os.path.join(logs_dir, log_filename)

    # Настраиваем ротацию по дням, храним неделю
    file_handler = TimedRotatingFileHandler(
        log_path, when='midnight', interval=1, backupCount=7, encoding='utf-8'
    )
    
    # Настройка формата вывода
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(formatter)

    # Настройка корневого логгера
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # Устанавливаем уровень логирования
    
    # Убираем старые хендлеры, чтобы не дублировать записи
    root_logger.handlers = []
    
    # Добавляем обработчик для записи в файл
    file_handler.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    
    # Добавляем обработчик для вывода в консоль
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Настраиваем логирование для asyncio
    logging.getLogger('asyncio').setLevel(logging.WARNING)
    
    logger = logging.getLogger(__name__)
    logger.info("Логгер инициализирован")
    return logger

def log_command_result(command, result, success=True):
    """Логирует результат выполнения команды."""
    logger = logging.getLogger(__name__)
    status = "SUCCESS" if success else "ERROR"
    
    # Форматируем вывод для лучшей читаемости
    if isinstance(result, dict):
        # Если результат - словарь, логируем его поля отдельно
        log_message = [
            f"Command: {command}",
            f"Status: {status}",
            f"Return code: {result.get('returncode', 'N/A')}",
            "--- STDOUT ---",
            result.get('stdout', ''),
            "--- STDERR ---",
            result.get('stderr', '')
        ]
        if 'timeout' in result and result['timeout']:
            log_message.append("TIMEOUT: Command execution timed out")
    else:
        # Иначе логируем как есть
        log_message = [f"Command: {command}", f"Result: {result}"]
    
    # Объединяем все строки в одно сообщение
    message = "\n".join(str(line) for line in log_message)
    
    # Записываем в соответствующий уровень логирования
    if success:
        logger.info(message)
    else:
        logger.error(message)
    
    # Возвращаем отформатированное сообщение на случай, если оно понадобится
    return message