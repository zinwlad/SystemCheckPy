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
    handler = TimedRotatingFileHandler(
        log_path, when='midnight', interval=1, backupCount=7, encoding='cp1251'
    )
    formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    handler.setFormatter(formatter)

    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # Убираем старые хендлеры, чтобы не дублировать записи
    logger.handlers = []
    logger.addHandler(handler)

def log_command_result(command, result, success=True):
    status = "SUCCESS" if success else "ERROR"
    message = f"Command: {command}\nResult: {result}"
    if success:
        logging.info(message)
    else:
        logging.error(message)