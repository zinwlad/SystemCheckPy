# system_checks.py
import subprocess
from typing import Optional, Tuple, Dict, Any

def _build_powershell_command(command: str) -> str:
    """
    Формирует безопасную команду запуска PowerShell. Минимизируем влияние спецсимволов,
    передавая выражение целиком в -Command. При необходимости дальнейшего усиления
    стоит перейти на сценарий с -File и аргументами.
    """
    # Принудительно:
    # - отключаем прогрессбар в консоли (ускоряет и не шумит)
    # - ширина строки для форматтеров (Format-Table/Format-List), чтобы не было переноса в несколько строк
    # - приводим вывод к строке (Out-String) для сохранения переносов
    # - кодировка UTF-8 на всякий случай
    ps_preamble = (
        "$ProgressPreference='SilentlyContinue'; "
        "[Console]::OutputEncoding = [System.Text.Encoding]::UTF8; "
        "$OutputEncoding = [System.Text.Encoding]::UTF8; "
    )
    wrapped = f"& {{ {command} | Out-String -Width 4096 }}"
    return f'powershell.exe -NoProfile -ExecutionPolicy Bypass -Command "{ps_preamble}{wrapped}"'

def launch_command(command: str) -> subprocess.Popen:
    """
    Запускает команду в PowerShell и возвращает объект процесса. Вывод захватывается как байты,
    чтобы затем безопасно декодировать с fallback по кодировкам.
    """
    powershell_command = _build_powershell_command(command)
    process = subprocess.Popen(
        powershell_command,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True
    )
    return process

def _decode_output(raw: Optional[bytes]) -> str:
    if raw is None:
        return ""
    # Сначала пробуем cp1251, затем UTF-8; в конце подстраховываемся replace
    for enc in ("cp1251", "utf-8"):
        try:
            return raw.decode(enc)
        except UnicodeDecodeError:
            continue
    return raw.decode("utf-8", errors="replace")

def collect_output(process: subprocess.Popen, timeout: int = 30) -> Dict[str, Any]:
    """
    Ожидает завершения процесса и возвращает словарь с stdout, stderr и кодом возврата.
    В случае таймаута процесс убивается и возвращается соответствующее сообщение об ошибке.
    { 'stdout': str, 'stderr': str, 'returncode': int, 'timeout': bool }
    """
    try:
        stdout_b, stderr_b = process.communicate(timeout=timeout)
        stdout = _decode_output(stdout_b).strip()
        stderr = _decode_output(stderr_b).strip()
        return {
            "stdout": stdout,
            "stderr": stderr,
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
        try:
            process.kill()
        except Exception:
            pass
        return {
            "stdout": "",
            "stderr": f"Неизвестная ошибка: {str(e)}",
            "returncode": -1,
            "timeout": False,
        }

def run_command(command: str, timeout: int = 30, details: bool = False):
    """
    Совместимая обёртка: по умолчанию возвращает строку stdout или сообщение об ошибке (как раньше),
    но при details=True возвращает словарь с полями stdout, stderr, returncode, timeout.
    """
    process = launch_command(command)
    result = collect_output(process, timeout=timeout)
    if details:
        return result
    # Режим совместимости со старыми вызовами
    if result["returncode"] != 0:
        err = result["stderr"] or "Ошибка выполнения команды"
        return f"Ошибка выполнения команды '{command}':\n{err}"
    return result["stdout"].strip()