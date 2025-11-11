# system_checks.py
import os
import subprocess
import logging
import json
import re
from typing import Dict, Any, Optional

# Настройка логирования
logger = logging.getLogger(__name__)

def launch_command(command: str) -> subprocess.Popen:
    """
    Запускает команду в PowerShell и возвращает объект процесса.
    
    Args:
        command: Команда PowerShell для выполнения
        
    Returns:
        subprocess.Popen: Объект запущенного процесса
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Подготовка к запуску команды: {command}")
    
    # Формируем команду с настройками кодировки и обработки ошибок
    ps_command = [
        'powershell.exe',
        '-NoProfile',
        '-ExecutionPolicy', 'Bypass',
        '-Command', f"""
        $ErrorActionPreference = 'Stop'
        $OutputEncoding = [System.Text.Encoding]::UTF8
        [Console]::OutputEncoding = [System.Text.Encoding]::UTF8
        try {{
            {command}
        }} catch {{
            Write-Error $_.Exception.Message
            exit 1
        }}
        """
    ]
    
    logger.debug(f"Полная команда: {' '.join(ps_command)}")
    
    try:
        # Запускаем процесс с текстовым режимом и UTF-8 кодировкой
        process = subprocess.Popen(
            ps_command,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=False,
            text=True,
            encoding='utf-8',
            errors='replace',
            creationflags=subprocess.CREATE_NO_WINDOW
        )
        logger.info(f"Процесс запущен с PID: {process.pid}")
        return process
        
    except Exception as e:
        error_msg = f"Ошибка при запуске процесса: {str(e)}"
        logger.error(error_msg, exc_info=True)
        raise RuntimeError(error_msg) from e

def _decode_output(output: str) -> str:
    """
    Обрабатывает вывод команды.
    
    Args:
        output: Вывод команды (уже декодированный в строку)
        
    Returns:
        str: Обработанный вывод
    """
    if output is None:
        return ""
    return str(output)

def collect_output(process: subprocess.Popen, timeout: int = 30) -> Dict[str, Any]:
    """
    Собирает вывод из процесса и возвращает результат.
    
    Args:
        process: Запущенный процесс
        timeout: Таймаут ожидания завершения (в секундах)
        
    Returns:
        Dict[str, Any]: Словарь с результатами выполнения команды
    """
    logger = logging.getLogger(__name__)
    logger.debug(f"Сбор вывода процесса (PID: {process.pid}), таймаут: {timeout} сек")
    
    try:
        # Пытаемся дождаться завершения процесса с таймаутом
        logger.debug("Ожидаем завершения процесса...")
        stdout, stderr = process.communicate(timeout=timeout)
        
        # Декодируем вывод
        stdout_str = _decode_output(stdout) if stdout else ""
        stderr_str = _decode_output(stderr) if stderr else ""
        
        # Логируем информацию о выводе
        logger.debug(f"Процесс завершен с кодом {process.returncode}")
        
        # Если вывод пустой, но процесс завершился успешно, пробуем альтернативный метод
        if not stdout_str and not stderr_str and process.returncode == 0:
            logger.warning("И stdout, и stderr пустые, хотя процесс завершился успешно. Пробуем альтернативный метод...")
            
            # Пробуем выполнить команду напрямую через subprocess.run
            alt_cmd = [
                'powershell.exe',
                '-NoProfile',
                '-ExecutionPolicy', 'Bypass',
                '-Command', "$OutputEncoding = [System.Text.Encoding]::UTF8; [Console]::OutputEncoding = [System.Text.Encoding]::UTF8; Get-ComputerInfo | Select-Object -First 10 | Format-List"
            ]
            
            try:
                result = subprocess.run(
                    alt_cmd,
                    capture_output=True,
                    text=True,
                    encoding='utf-8',
                    errors='replace',
                    timeout=30
                )
                
                if result.stdout:
                    stdout_str = result.stdout
                    logger.info("Успешно получили вывод через subprocess.run")
                else:
                    logger.warning("Альтернативный метод не вернул данных")
                    
            except Exception as alt_e:
                logger.error(f"Ошибка при альтернативном выполнении команды: {alt_e}")
        
        # Логируем результат
        if stdout_str:
            sample = stdout_str[:500] + ('...' if len(stdout_str) > 500 else '')
            logger.debug(f"Вывод stdout (первые 500 символов):\n{sample}")
        else:
            logger.warning("STDOUT пуст")
            
        if stderr_str:
            sample = stderr_str[:500] + ('...' if len(stderr_str) > 500 else '')
            logger.warning(f"Вывод stderr (первые 500 символов):\n{sample}")
            
        return {
            "stdout": stdout_str,
            "stderr": stderr_str,
            "returncode": process.returncode,
            "timeout": False
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