import subprocess
import os
import datetime
from colorama import Fore, Style, init

init(autoreset=True)  # Инициализация colorama для Windows

LOG_FILE = "system_check_log.txt"

def run_command(command):
    """Выполняет указанную команду и записывает результат в лог-файл."""
    try:
        print(f"{Fore.CYAN}Запуск команды: {command}")
        result = subprocess.run(command, shell=True, text=True, capture_output=True)
        log_result(command, result.stdout, result.stderr)
        print(f"{Fore.GREEN}Команда выполнена. Результат сохранён в лог.")
    except Exception as e:
        print(f"{Fore.RED}Ошибка при выполнении команды {command}: {e}")
        log_result(command, "", str(e))

def log_result(command, stdout, stderr):
    """Записывает результат выполнения команды в лог-файл."""
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(LOG_FILE, "a", encoding="utf-8") as log_file:
        log_file.write(f"=== {timestamp} ===\n")
        log_file.write(f"Команда: {command}\n")
        log_file.write(f"Результат:\n{stdout}\n")
        if stderr:
            log_file.write(f"Ошибки:\n{stderr}\n")
        log_file.write("\n")

def read_log():
    """Читает и отображает содержимое лог-файла."""
    if os.path.exists(LOG_FILE):
        with open(LOG_FILE, "r", encoding="utf-8") as log_file:
            print(f"{Fore.YELLOW}Последние результаты:\n")
            print(log_file.read())
    else:
        print(f"{Fore.RED}Лог-файл не найден. Выполните проверку для создания логов.")

def main():
    print(f"{Fore.BLUE}=== SystemCheckPy ===")
    print("Программа для диагностики системы.")
    print("Выберите действие:")
    
    options = {
        1: "sfc /scannow",
        2: "chkdsk C: /f /r /x",
        3: "ipconfig /all",
        4: "netstat -an",
        5: "Ввести свою команду",
        6: "Просмотреть лог"
    }

    for key, value in options.items():
        print(f"{key}: {value}")

    try:
        choice = int(input("Введите номер действия: "))
        if choice in options:
            if choice == 5:  # Пользовательская команда
                custom_command = input("Введите вашу команду: ")
                run_command(custom_command)
            elif choice == 6:  # Просмотр логов
                read_log()
            else:
                run_command(options[choice])
        else:
            print(f"{Fore.RED}Неверный выбор!")
    except ValueError:
        print(f"{Fore.RED}Ошибка! Введите число.")

if __name__ == "__main__":
    main()
