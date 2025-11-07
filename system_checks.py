# system_checks.py
import subprocess
import logging
import json
import re
from typing import Optional, Tuple, Dict, Any

# Настройка логирования
logger = logging.getLogger(__name__)

def _build_powershell_command(command: str) -> str:
    """
    Формирует безопасную команду запуска PowerShell с правильной обработкой вывода.
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Собираем команду PowerShell для: {command}")
    
    # Настройки для корректного отображения русского текста и работы с кодировкой
    ps_preamble = (
        "$OutputEncoding = [System.Text.Encoding]::UTF8; "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "$PSDefaultParameterValues['*:Encoding'] = 'utf8'; "
        "$ProgressPreference = 'SilentlyContinue'; "
        "$ErrorActionPreference = 'Continue'; "
        "Write-Host '=== НАЧАЛО ВЫВОДА КОМАНДЫ ==='; "
    )
    
    # Оборачиваем команду в блок try-catch для перехвата ошибок
    wrapped = (
        f"try {{ {command} | Out-String -Width 4096; \"`n[Exit Code: $LASTEXITCODE]\" }} "
        "catch {{ $_ | Out-String -Width 4096; \"`n[Exit Code: 1]\"; exit 1 }}; "
        "Write-Host '=== КОНЕЦ ВЫВОДА КОМАНДЫ ===';"
    )
    
    # Формируем полную команду
    full_command = (
        'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command '
        f'"{ps_preamble}{wrapped}"'
    )
    
    logger.debug(f"Сформирована команда PowerShell: {full_command}")
    return full_command

def launch_command(command: str) -> subprocess.Popen:
    """
    Запускает команду в PowerShell и возвращает объект процесса.
    """
    logger = logging.getLogger(__name__)
    logger.info(f"Запуск команды: {command}")
    
    # Строим команду PowerShell с правильными настройками
    powershell_command = _build_powershell_command(command)
    
    # Настройки для запуска процесса
    startupinfo = subprocess.STARTUPINFO()
    startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
    startupinfo.wShowWindow = subprocess.SW_HIDE
    
    # Создаем процесс с правильными настройками
    try:
        logger.debug("Запуск процесса PowerShell...")
        process = subprocess.Popen(
            powershell_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            stdin=subprocess.PIPE,
            shell=True,
            startupinfo=startupinfo,
            creationflags=subprocess.CREATE_NO_WINDOW,
            text=False,
            bufsize=-1,  # Используем буфер по умолчанию
            universal_newlines=False
        )
        logger.info(f"Процесс запущен с PID: {process.pid}")
        return process
    except Exception as e:
        error_msg = f"Ошибка при запуске процесса: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e

def _decode_output(output: bytes) -> str:
    """
    Декодирует вывод команды с учетом кодировки.
    """
    if not output:
        return ""
        
    logger = logging.getLogger(__name__)
    
    # Список кодировок для попытки декодирования
    encodings = ['cp1251', 'utf-8', 'cp866', 'iso-8859-1']
    
    for encoding in encodings:
        try:
            decoded = output.decode(encoding)
            logger.debug(f"Успешно декодировано с кодировкой {encoding}")
            return decoded
        except UnicodeDecodeError:
            continue
    
    # Если ни одна кодировка не сработала, используем замену нечитаемых символов
    logger.warning("Не удалось декодировать вывод с использованием стандартных кодировок, используется замена символов")
    return output.decode(errors='replace')

def collect_output(process: subprocess.Popen, timeout: int = 30) -> Dict[str, Any]:
    """
    Ожидает завершения процесса и возвращает словарь с stdout, stderr и кодом возврата.
    В случае таймаута процесс убивается и возвращается соответствующее сообщение об ошибке.
    { 'stdout': str, 'stderr': str, 'returncode': int, 'timeout': bool }
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Сбор вывода процесса (PID: {process.pid}), таймаут: {timeout} сек")
    
    # Функция для безопасного чтения вывода
    def read_output(stream, buffer):
        try:
            while True:
                line = stream.readline()
                if not line:
                    break
                buffer.append(line)
                logger.debug(f"Получена строка вывода: {line.decode('utf-8', errors='replace').strip()}")
        except Exception as e:
            logger.error(f"Ошибка при чтении вывода: {str(e)}")
    
    # Запускаем потоки для чтения вывода
    stdout_buffer = []
    stderr_buffer = []
    
    from threading import Thread
    stdout_thread = Thread(target=read_output, args=(process.stdout, stdout_buffer))
    stderr_thread = Thread(target=read_output, args=(process.stderr, stderr_buffer))
    
    stdout_thread.start()
    stderr_thread.start()
    
    try:
        # Ожидаем завершения процесса с таймаутом
        process.wait(timeout=timeout)
        
        # Дожидаемся завершения потоков чтения
        stdout_thread.join(timeout=5)
        stderr_thread.join(timeout=5)
        
        # Получаем вывод
        stdout = b''.join(stdout_buffer) if stdout_buffer else b''
        stderr = b''.join(stderr_buffer) if stderr_buffer else b''
        
        # Декодируем вывод
        stdout_str = _decode_output(stdout)
        stderr_str = _decode_output(stderr)
        
        # Логируем часть вывода для отладки
        if stdout_str:
            sample = stdout_str[:200] + ('...' if len(stdout_str) > 200 else '')
            logger.debug(f"Вывод stdout (первые 200 символов): {sample}")
        if stderr_str:
            sample = stderr_str[:200] + ('...' if len(stderr_str) > 200 else '')
            logger.debug(f"Вывод stderr (первые 200 символов): {sample}")
            
        return {
            "stdout": stdout_str,
            "stderr": stderr_str,
            "returncode": process.returncode,
            "timeout": False,
        }
    except subprocess.TimeoutExpired:
        process.kill()
        return {
            "stdout": "",
            "stderr": f"Превышено время ожидания ({timeout} сек)",
            "returncode": -1,
            "timeout": True,
        }
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Ошибка при сборе вывода: {error_msg}", exc_info=True)
        try:
            process.kill()
        except Exception as kill_error:
            logger.warning(f"Не удалось завершить процесс: {kill_error}")
        return {
            "stdout": "",
            "stderr": f"Ошибка выполнения команды: {error_msg}",
            "returncode": -1,
            "timeout": False,
        }

def run_command(command: str, timeout: int = 30, details: bool = False):
    """
    Совместимая обёртка: по умолчанию возвращает строку stdout или сообщение об ошибке (как раньше),
    но при details=True возвращает словарь с полями stdout, stderr, returncode, timeout.
    """
    logger.info(f"Выполнение команды: {command}")
    try:
        process = launch_command(command)
        result = collect_output(process, timeout=timeout)
        
        if details:
            logger.debug(f"Возвращаем детализированный результат: {result}")
            return result
            
        # Режим совместимости со старыми вызовами
        if result["returncode"] != 0:
            err = result["stderr"] or "Ошибка выполнения команды"
            logger.warning(f"Ошибка выполнения команды (код {result['returncode']}): {err}")
            return f"Ошибка выполнения команды '{command}':\n{err}"
            
        logger.debug(f"Успешное выполнение, возвращаем результат")
        return result["stdout"].strip()
        
    except Exception as e:
        error_msg = f"Непредвиденная ошибка при выполнении команды '{command}': {str(e)}"
        logger.error(error_msg, exc_info=True)
        if details:
            return {
                "stdout": "",
                "stderr": error_msg,
                "returncode": -1,
                "timeout": False,
                "error": str(e)
            }
        return error_msg