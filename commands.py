# commands.py
commands = {
    "Получить информацию о системе": {
        "description": "Показывает общую информацию о системе: ОС, процессор, память и т.д.",
        "command": "try { $os = Get-CimInstance -ClassName Win32_OperatingSystem; $cpu = Get-CimInstance -ClassName Win32_Processor; $comp = Get-CimInstance -ClassName Win32_ComputerSystem; $props = @{ 'Операционная система' = $os.Caption; 'Версия ОС' = $os.Version; 'Архитектура' = $os.OSArchitecture; 'Производитель' = $comp.Manufacturer; 'Модель' = $comp.Model; 'Имя компьютера' = $comp.Name; 'Пользователь' = $comp.UserName; 'Процессор' = $cpu.Name; 'Количество ядер' = $cpu.NumberOfCores; 'Логических процессоров' = $cpu.NumberOfLogicalProcessors; 'Объем ОЗУ (ГБ)' = [math]::Round($comp.TotalPhysicalMemory/1GB, 2); 'Время работы' = (Get-Date) - $os.LastBootUpTime }; $props | Format-List } catch { Write-Error \"Ошибка при получении информации о системе: $_\"; exit 1 }"
    },
    "Получить конфигурацию IP": {
        "description": "Отображает полную конфигурацию сети, включая IP-адреса, DNS-серверы и шлюзы",
        "command": "Get-NetIPConfiguration | Format-List -Property *"
    },
    "Получить сетевые адаптеры": {
        "description": "Показывает список всех сетевых адаптеров с их статусом, скоростью и типом подключения",
        "command": "Get-NetAdapter | Format-Table -Property Name, Status, LinkSpeed, MediaType, PhysicalMediaType -AutoSize"
    },
    "Получить кэш DNS": {
        "description": "Отображает содержимое кэша DNS для диагностики проблем с разрешением имен",
        "command": "Get-DnsClientCache | Format-Table -Property Entry, Data, TimeToLive -AutoSize"
    },
    "Получить статистику сети": {
        "description": "Анализ активных TCP-подключений с группировкой по состоянию и портам",
        "command": "Get-NetTCPConnection | Group-Object -Property State, RemotePort | Format-Table -Property Name, Count -AutoSize"
    },
    "Получить информацию о системе": {
        "description": "Подробная информация о системе: ОС, процессор, память и т.д.",
        "command": "Get-ComputerInfo | Format-List -Property WindowsProductName, WindowsVersion, CsTotalPhysicalMemory, CsProcessors"
    },
    "Получить текущего пользователя": {
        "description": "Показывает имя текущего пользователя системы",
        "command": "Get-CimInstance -ClassName Win32_ComputerSystem | Select-Object -Property UserName | Format-Table -HideTableHeaders"
    },
    "Получить имя хоста": {
        "description": "Отображает имя компьютера в сети",
        "command": "$env:COMPUTERNAME"
    },
    "Получить состояние дисков": {
        "description": "Состояние всех дисков: буква, метка, размер, свободное место",
        "command": "Get-Volume | Format-Table -Property DriveLetter, FileSystemLabel, Size, SizeRemaining -AutoSize"
    },
    "Получить запущенные службы": {
        "description": "Список всех запущенных служб с их именами и статусом",
        "command": "Get-Service | Where-Object {$_.Status -eq 'Running'} | Format-Table -Property Name, DisplayName, Status -AutoSize"
    },
    "Получить запущенные процессы": {
        "description": "Топ-10 процессов по использованию CPU с именем, CPU и памятью",
        "command": "Get-Process | Sort-Object CPU -Descending | Select-Object -First 10 -Property Name, CPU, WorkingSet | Format-Table -AutoSize"
    },
    "Получить температуру процессора": {
        "description": "Текущая температура процессора в градусах Цельсия (если поддерживается оборудованием)",
        "command": "try { $temp = (Get-CimInstance -Namespace root/wmi -ClassName MSAcpi_ThermalZoneTemperature).CurrentTemperature; if ($temp) { [math]::Round(($temp / 10) - 273.15, 2) } else { 'Температура не поддерживается' } } catch { 'Ошибка: данные недоступны' }"
    },
    "Получить загрузку процессора": {
        "description": "Текущая загрузка процессора в процентах для всех ядер",
        "command": "Get-CimInstance -ClassName Win32_Processor | Select-Object -Property LoadPercentage | Format-Table -HideTableHeaders"
    },
    "Получить использование памяти": {
        "description": "Использование оперативной памяти в процентах и объёме",
        "command": "Get-CimInstance -ClassName Win32_OperatingSystem | Select-Object -Property @{Name='Использование (%)';Expression={[math]::Round((1 - $_.FreePhysicalMemory/$_.TotalVisibleMemorySize) * 100, 2)}}, @{Name='Свободно (МБ)';Expression={[math]::Round($_.FreePhysicalMemory/1024, 2)}} | Format-Table -AutoSize"
    },
    "Получить использование дисков": {
        "description": "Подробная информация об использовании дисков: размер, свободно, занято",
        "command": "Get-CimInstance -ClassName Win32_LogicalDisk | Select-Object -Property DeviceID, @{Name='Размер (ГБ)';Expression={[math]::Round($_.Size/1GB,2)}}, @{Name='Свободно (ГБ)';Expression={[math]::Round($_.FreeSpace/1GB,2)}}, @{Name='Занято (%)';Expression={[math]::Round(($_.Size-$_.FreeSpace)/$_.Size*100,2)}} | Format-Table -AutoSize"
    },
    "Получить обновления Windows": {
        "description": "Последние 10 установленных обновлений Windows с датой установки",
        "command": "Get-HotFix | Sort-Object InstalledOn -Descending | Select-Object -First 10 -Property HotFixID, Description, InstalledOn | Format-Table -AutoSize"
    },
    "Получить установленное ПО": {
        "description": "Список установленного ПО с названиями и версиями",
        "command": "try { Get-Package | Select-Object -Property Name, Version | Sort-Object Name | Format-Table -AutoSize } catch { 'Не удалось получить список через Get-Package' }"
    },
    "Получить сетевые подключения": {
        "description": "Активные сетевые подключения с локальными и удалёнными адресами",
        "command": "Get-NetTCPConnection | Where-Object State -eq 'Established' | Format-Table -Property LocalAddress, LocalPort, RemoteAddress, RemotePort -AutoSize"
    },
    "Получить журнал событий": {
        "description": "Последние 10 системных событий с датой и описанием",
        "command": "Get-EventLog -LogName System -Newest 10 | Format-Table -Property TimeGenerated, EntryType, Source, Message -AutoSize"
    },
    "Получить запланированные задачи": {
        "description": "Список активных задач с именем, состоянием и временем последнего запуска",
        "command": "Get-ScheduledTask | Where-Object {$_.State -ne 'Disabled'} | Format-Table -Property TaskName, State, LastRunTime -AutoSize"
    },
    "Получить установленные драйверы": {
        "description": "Список установленных драйверов с именами и версиями",
        "command": "Get-CimInstance -ClassName Win32_PnPSignedDriver | Select-Object -Property DeviceName, DriverVersion | Sort-Object DeviceName | Format-Table -AutoSize"
    },
    "Получить групповые политики": {
        "description": "Генерирует и открывает HTML-отчет о применённых групповых политиках",
        "command": "Get-GPResultantSetOfPolicy -ReportType Html -Path $env:TEMP\\GPReport.html; Invoke-Item $env:TEMP\\GPReport.html"
    },
    "Получить отчет о батарее": {
        "description": "Генерирует и открывает HTML-отчет о состоянии батареи (для ноутбуков)",
        "command": "powercfg /batteryreport /output \"$env:TEMP\\battery-report.html\"; Invoke-Item \"$env:TEMP\\battery-report.html\""
    },
    "Получить подробную статистику сети": {
        "description": "Подробная статистика сетевых адаптеров: принятые и отправленные данные",
        "command": "Get-NetAdapterStatistics | Format-Table -Property Name, ReceivedBytes, SentBytes, ReceivedUnicastPackets, SentUnicastPackets -AutoSize"
    },
    "Получить правила брандмауэра": {
        "description": "Список активных правил брандмауэра с именем, направлением и действием",
        "command": "Get-NetFirewallRule | Where-Object Enabled -eq 'True' | Select-Object -Property DisplayName, Direction, Action | Format-Table -AutoSize"
    },
    "Получить время работы системы": {
        "description": "Время с последней перезагрузки системы",
        "command": "Get-CimInstance -ClassName Win32_OperatingSystem | Select-Object -Property @{Name='Время последней загрузки';Expression={$_.LastBootUpTime}} | Format-Table -AutoSize"
    },
    "Получить информацию о BIOS": {
        "description": "Информация о BIOS: производитель, версия, дата выпуска",
        "command": "Get-CimInstance -ClassName Win32_BIOS | Select-Object -Property Manufacturer, Name, ReleaseDate | Format-Table -AutoSize"
    },
    "Получить информацию о GPU": {
        "description": "Информация о графическом процессоре: модель, версия драйвера, объем памяти",
        "command": "Get-CimInstance -ClassName Win32_VideoController | Select-Object -Property Name, DriverVersion, @{Name='AdapterRAM (ГБ)';Expression={[math]::Round($_.AdapterRAM/1GB,2)}} | Format-Table -AutoSize"
    },
    "Получить план питания": {
        "description": "Отображает текущий активный план управления питанием",
        "command": "powercfg /getactivescheme"
    },
    "Получить USB-устройства": {
        "description": "Список подключённых USB-устройств с именами и ID",
        "command": "Get-CimInstance -ClassName Win32_PnPEntity | Where-Object { $_.PNPClass -eq 'USB' -or $_.Name -match 'USB' } | Select-Object -Property Name, DeviceID | Format-Table -AutoSize"
    },
    "Получить состояние принтеров": {
        "description": "Список установленных принтеров с их статусом",
        "command": "Get-CimInstance -ClassName Win32_Printer | Select-Object -Property Name, Status, Default | Format-Table -AutoSize"
    },
    "Получить ожидающие обновления": {
        "description": "Список обновлений Windows, ожидающих установки (требуется модуль PSWindowsUpdate)",
        "command": "try { Get-WindowsUpdate | Select-Object -Property KBArticleID, Title, Size | Format-Table -AutoSize } catch { 'Модуль PSWindowsUpdate не установлен' }"
    },
    "Получить активные подключения": {
        "description": "Все активные сетевые подключения с IP и портами",
        "command": "Get-NetTCPConnection | Where-Object State -eq 'Established' | Format-Table -Property LocalAddress, LocalPort, RemoteAddress, RemotePort -AutoSize"
    },
    "Получить локальные настройки": {
        "description": "Текущие настройки региона и языка системы",
        "command": "Get-WinSystemLocale | Format-List -Property *"
    },
    "Получить данные SMART дисков": {
        "description": "Состояние дисков по SMART (если поддерживается)",
        "command": "Get-CimInstance -Namespace root/wmi -ClassName MSStorageDriver_FailurePredictStatus | Select-Object -Property PredictFailure, Reason | Format-Table -AutoSize"
    },
    "Получить сетевые ресурсы": {
        "description": "Список расшаренных сетевых ресурсов на компьютере",
        "command": "Get-CimInstance -ClassName Win32_Share | Select-Object -Property Name, Path | Format-Table -AutoSize"
    },
    "Получить информацию о часовой зоне": {
        "description": "Текущая временная зона и её настройки",
        "command": "Get-TimeZone | Format-List -Property *"
    },
    "Получить аудиоустройства": {
        "description": "Список подключённых аудиоустройств и их статус",
        "command": "Get-CimInstance -ClassName Win32_SoundDevice | Select-Object -Property Name, Status | Format-Table -AutoSize"
    },
    "Проверить производительность дисков": {
        "description": "Текущая производительность дисков: очередь, чтение, запись",
        "command": "Get-CimInstance Win32_PerfFormattedData_PerfDisk_LogicalDisk | Select-Object -Property Name, AvgDiskQueueLength, DiskReadsPerSec, DiskWritesPerSec | Format-Table -AutoSize"
    },
    "Проверить уровень сигнала Wi-Fi": {
        "description": "Уровень сигнала Wi-Fi в процентах (работает только для беспроводных адаптеров)",
        "command": "try { $wifi = Get-NetAdapter | Where-Object { $_.PhysicalMediaType -match '802.11' -and $_.Status -eq 'Up' }; if ($wifi) { (netsh wlan show interfaces | Select-String 'Signal') -replace '.*Signal\\s*:\s*(\\d+)%.*', '$1' } else { 'Wi-Fi адаптер не найден или отключён' } } catch { 'Ошибка: данные недоступны' }"
    },
    "Проверить скорость интернета": {
        "description": "Тестирование скорости интернета (требуется Speedtest CLI)",
        "command": "try { speedtest-cli --simple } catch { 'Установите Speedtest CLI: pip install speedtest-cli' }"
    },
    "Получить температуру GPU": {
        "description": "Текущая температура видеокарты (требуется сторонний инструмент, например, nvidia-smi)",
        "command": "try { nvidia-smi --query-gpu=temperature.gpu --format=csv,noheader } catch { 'Требуется nvidia-smi или драйверы NVIDIA' }"
    },
    "Проверить целостность системных файлов": {
        "description": "Проверка и восстановление системных файлов Windows",
        "command": "sfc /scannow",
        "requires_admin": True
    },
    "Получить список пользователей": {
        "description": "Список всех локальных пользователей системы",
        "command": "Get-LocalUser | Select-Object -Property Name, Enabled, LastLogon | Format-Table -AutoSize"
    },
    "Получить информацию о материнской плате": {
        "description": "Информация о материнской плате: производитель, модель",
        "command": "Get-CimInstance -ClassName Win32_BaseBoard | Select-Object -Property Manufacturer, Product | Format-Table -AutoSize"
    },
    "Проверить состояние сети": {
        "description": "Пинг до Google DNS для проверки подключения",
        "command": "ping 8.8.8.8 -n 4"
    },
    "Получить список установленных шрифтов": {
        "description": "Список всех установленных шрифтов в системе",
        "command": "Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows NT\\CurrentVersion\\FontSubstitutes' | Format-Table -AutoSize"
    },
    "Выполнить CHKDSK": {
        "description": "Проверка и восстановление файловой системы",
        "command": "chkdsk C: /f /r /x",
        "requires_admin": True
    },
    "Выполнить DISM": {
        "description": "Проверка и восстановление системных файлов и компонентов",
        "command": "dism /online /cleanup-image /restorehealth",
        "requires_admin": True
    },
    "Мониторинг батареи (расширенный)": {
        "description": "Генерирует отчет об энергопотреблении системы (HTML)",
        "command": "powercfg /energy /output \"$env:TEMP\\energy-report.html\"; Invoke-Item \"$env:TEMP\\energy-report.html\"",
        "requires_admin": True
    },
    "Проверка целостности загрузочного сектора": {
        "description": "Сканирование загрузочных записей для устранения проблем с загрузкой",
        "command": "bootrec /scanos",
        "requires_recovery": True
    },
    "Получение MAC-адреса": {
        "description": "Список MAC-адресов всех сетевых адаптеров",
        "command": "Get-NetAdapter | Select-Object -Property Name, MacAddress | Format-Table -AutoSize"
    },
    "Проверка обновлений драйверов": {
        "description": "Сканирование и обновление драйверов устройств",
        "command": "pnputil /scan-devices",
        "requires_admin": True
    },
    "Мониторинг производительности системы": {
        "description": "Измерение загрузки процессора в реальном времени",
        "command": "Get-Counter -Counter '\\Processor(_Total)\\% Processor Time' -SampleInterval 2 -MaxSamples 5 | Select-Object -ExpandProperty CounterSamples | Select-Object -Property CookedValue | Format-Table -AutoSize"
    },
    "Получение списка открытых файлов": {
        "description": "Список файлов, открытых по сети",
        "command": "Get-SmbOpenFile | Format-Table -Property FileName, Path, ClientUserName -AutoSize",
        "requires_admin": True
    },
    "Проверка сертификатов": {
        "description": "Список установленных сертификатов с датой истечения",
        "command": "Get-ChildItem -Path Cert:\\LocalMachine\\My | Select-Object -Property Subject, NotAfter | Format-Table -AutoSize"
    },
    "Очистка временных файлов": {
        "description": "Удаление временных файлов из папки TEMP",
        "command": "Remove-Item -Path $env:TEMP\\* -Recurse -Force -ErrorAction SilentlyContinue",
        "requires_admin": True
    },
    "Получение списка установленных расширений браузера": {
        "description": "Список расширений для Microsoft Edge",
        "command": "Get-ItemProperty -Path 'HKLM:\\Software\\Wow6432Node\\Microsoft\\Edge\\Extensions' | Format-Table -AutoSize"
    },
    "Проверка использования портов": {
        "description": "Список активных портов и связанных процессов",
        "command": "netstat -aon | FindStr LISTENING"
    },
    "Получение информации о RAM": {
        "description": "Детали физической памяти: производитель, модель, объем",
        "command": "Get-CimInstance -ClassName Win32_PhysicalMemory | Select-Object -Property Manufacturer, PartNumber, @{Name='Capacity (ГБ)';Expression={[math]::Round($_.Capacity/1GB,2)}} | Format-Table -AutoSize"
    },
    "Проверка статуса антивируса": {
        "description": "Состояние установленного антивирусного ПО",
        "command": "Get-CimInstance -Namespace root/SecurityCenter2 -ClassName AntiVirusProduct | Select-Object -Property displayName, productState | Format-Table -AutoSize"
    },
    "Состояние брандмауэра": {
        "description": "Состояние профилей брандмауэра Windows",
        "command": "Get-NetFirewallProfile | Select-Object -Property Name, Enabled | Format-Table -AutoSize"
    },
    "Таблица ARP": {
        "description": "Содержимое ARP-таблицы",
        "command": "arp -a"
    },
    "Кэш DNS": {
        "description": "Текущий кэш DNS",
        "command": "ipconfig /displaydns"
    },
    "Маршруты": {
        "description": "Таблица маршрутизации",
        "command": "route print"
    },
    "Системные события (последние 50)": {
        "description": "Последние события из журнала System",
        "command": "Get-WinEvent -LogName System -MaxEvents 50 | Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize"
    },
    "Журнал Application (последние 50)": {
        "description": "Последние события из журнала Application",
        "command": "Get-WinEvent -LogName Application -MaxEvents 50 | Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize"
    },
    "Журнал Setup (последние 50)": {
        "description": "Последние события из журнала Setup",
        "command": "Get-WinEvent -LogName Setup -MaxEvents 50 | Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize"
    },
    "Трассировка маршрута (tracert)": {
        "description": "Выполнить tracert до указанного хоста или IP",
        "template": "tracert \"{input}\"",
        "input_prompt": "Введите хост или IP для трассировки",
        "input_pattern": "(?:\\d{1,3}(?:\\.\\d{1,3}){3}|[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*)",
        "input_example": "8.8.8.8 или example.com"
    },
    "Resolve-DnsName": {
        "description": "Разрешить имя хоста с помощью Resolve-DnsName",
        "template": "Resolve-DnsName -Name \"{input}\" | Select-Object Name, Type, IPAddress | Format-Table -AutoSize",
        "input_prompt": "Введите доменное имя для разрешения",
        "input_pattern": "[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*",
        "input_example": "example.com"
    },
    "Статус службы по имени": {
        "description": "Показать состояние службы по имени",
        "template": "Get-Service -Name \"{input}\" | Select-Object Name, DisplayName, Status | Format-Table -AutoSize",
        "input_prompt": "Введите точное имя службы (Name)",
        "input_pattern": "[A-Za-z0-9_.-]{2,64}",
        "input_example": "Spooler или wuauserv"
    },
    "Получить список запланированных задач (все)": {
        "description": "Отображает все задачи в запланированном задании, включая отключенные",
        "command": "Get-ScheduledTask | Format-Table -Property TaskName, State, TaskPath -AutoSize"
    },
    "Проверить время работы системы (подробно)": {
        "description": "Показывает дату и время последней перезагрузки, а также общее время работы",
        "command": "$os = Get-CimInstance Win32_OperatingSystem; $uptime = (Get-Date) - $os.LastBootUpTime; Write-Output \"Последняя перезагрузка: $($os.LastBootUpTime)\"; Write-Output \"Время работы: $($uptime.Days) дней, $($uptime.Hours) часов, $($uptime.Minutes) минут\""
    },
    "Проверить файлы с атрибутом 'System'": {
        "description": "Находит файлы в корне системного диска с атрибутом 'System' (может быть полезно для диагностики)",
        "command": "Get-ChildItem -Path C:\\ -Attributes System -ErrorAction SilentlyContinue | Format-Table -Property Name, LastWriteTime -AutoSize",
        "requires_admin": True
    },

    # --- Сеть ---
    "Проверить соединение (ping)": {
        "description": "Выполнить ping до указанного хоста или IP",
        "template": "ping \"{input}\" -n 4",
        "input_prompt": "Введите хост или IP для проверки соединения",
        "input_pattern": "(?:\\d{1,3}(?:\\.\\d{1,3}){3}|[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?(?:\\.[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?)*)",
        "input_example": "google.com или 192.168.1.1"
    },
    "Проверить открытые порты (netstat)": {
        "description": "Список прослушиваемых портов и связанных процессов",
        "command": "netstat -anp tcp | Select-String LISTENING"
    },
    "Проверить DNS-сервера": {
        "description": "Отображает текущие DNS-серверы, используемые сетевыми адаптерами",
        "command": "Get-DnsClientServerAddress -AddressFamily IPv4 | Select-Object InterfaceAlias, ServerAddresses"
    },
    "Очистить кэш DNS": {
        "description": "Очищает локальный кэш DNS",
        "command": "Clear-DnsClientCache",
        "requires_admin": True
    },
    "Сброс конфигурации сети": {
        "description": "Сбрасывает настройки TCP/IP и кэш DNS (требует перезагрузки для полного эффекта)",
        "command": "netsh int ip reset && netsh winsock reset && ipconfig /flushdns",
        "requires_admin": True
    },

    # --- Безопасность ---
    "Проверить статус Windows Defender": {
        "description": "Проверяет статус основных компонентов Windows Defender",
        "command": "Get-MpComputerStatus | Select-Object -Property AntivirusEnabled, AntispywareEnabled, NISEnabled, RealTimeProtectionEnabled"
    },
    "Проверить список запрещенных программ Windows Defender": {
        "description": "Показывает список файлов и папок, игнорируемых Windows Defender",
        "command": "Get-MpPreference | Select-Object -ExpandProperty ExclusionPath"
    },
    "Проверить список пользователей в группе администраторов": {
        "description": "Отображает пользователей, входящих в группу 'Администраторы'",
        "command": "Get-LocalGroupMember -Group 'Administrators' | Select-Object -Property Name, PrincipalSource | Format-Table -AutoSize"
    },
    "Проверить статус UAC": {
        "description": "Проверяет текущий уровень уведомлений UAC",
        "command": "Get-ItemProperty -Path 'HKLM:\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Policies\\System' -Name ConsentPromptBehaviorAdmin | Select-Object -ExpandProperty ConsentPromptBehaviorAdmin"
    },

    # --- Журналы ---
    "Найти ошибки в системном журнале за последние 24ч": {
        "description": "Поиск событий уровня 'Ошибка' в журнале System за последние 24 часа",
        "command": "$time = (Get-Date).AddHours(-24); Get-WinEvent -FilterHashtable @{LogName='System'; Level=1,2,3; StartTime=$time} -ErrorAction SilentlyContinue | Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize"
    },
    "Найти ошибки в журнале Application за последние 24ч": {
        "description": "Поиск событий уровня 'Ошибка' в журнале Application за последние 24 часа",
        "command": "$time = (Get-Date).AddHours(-24); Get-WinEvent -FilterHashtable @{LogName='Application'; Level=1,2,3; StartTime=$time} -ErrorAction SilentlyContinue | Select-Object TimeCreated, Id, LevelDisplayName, Message | Format-Table -AutoSize"
    },

    # --- Управление дисками и файлами ---
    "Проверить диски на ошибки (PowerShell)": {
        "description": "Запускает проверку дисков на наличие ошибок (аналог chkdsk /f без перезагрузки)",
        "command": "Get-Volume | Where-Object {$_.DriveType -eq 'Fixed'} | ForEach-Object { $drive = $_.DriveLetter; Write-Output \"Проверка диска $drive:`\"; Repair-Volume -DriveLetter $drive -Scan -CimSession localhost }",
        "requires_admin": True
    },
    "Получить список файлов по размеру": {
        "description": "Список 100 самых больших файлов на диске C:",
        "command": "Get-ChildItem -Path C:\\ -Recurse -File -ErrorAction SilentlyContinue | Sort-Object Length -Descending | Select-Object -First 100 -Property Name, @{Name='Size(MB)';Expression={[math]::Round($_.Length/1MB,2)}}, DirectoryName | Format-Table -AutoSize"
    },
    "Проверить дисковое пространство (все диски, подробно)": {
        "description": "Подробная информация о свободном и занятом месте на всех дисках",
        "command": "Get-WmiObject -Class Win32_LogicalDisk | Where-Object {$_.DriveType -eq 3} | Select-Object DeviceID, VolumeName, @{Name='Размер (ГБ)';Expression={[math]::Round($_.Size/1GB,2)}}, @{Name='Свободно (ГБ)';Expression={[math]::Round($_.FreeSpace/1GB,2)}}, @{Name='Занято (%)';Expression={[math]::Round((($_.Size-$_.FreeSpace)/$_.Size)*100,2)}} | Format-Table -AutoSize"
    },

    # --- Управление системой ---
    "Перезагрузить систему": {
        "description": "Перезагружает систему через 60 секунд с сообщением",
        "command": "Restart-Computer -ComputerName localhost -Force -WhatIf", # Добавьте -Confirm:$false если нужно выполнить
        "requires_admin": True
    },
    "Выключить систему": {
        "description": "Выключает систему через 60 секунд с сообщением",
        "command": "Stop-Computer -ComputerName localhost -Force -WhatIf", # Добавьте -Confirm:$false если нужно выполнить
        "requires_admin": True
    },
    "Проверить обновления (только информация)": {
        "description": "Проверяет наличие доступных обновлений (требует модуль PSWindowsUpdate)",
        "command": "try { Get-WindowsUpdate -Download | Select-Object -Property KBArticleID, Title | Format-Table -AutoSize } catch { 'Модуль PSWindowsUpdate не установлен или обновления недоступны' }"
    },
    "Проверить статус служб Windows Update": {
        "description": "Проверяет статус служб, связанных с обновлениями Windows",
        "command": "Get-Service -Name wuauserv, bits, cryptsvc, msiserver | Select-Object Name, Status, StartType | Format-Table -AutoSize"
    },
    "Очистить диски (Disk Cleanup) - GUI": {
        "description": "Запускает встроенный мастер очистки дисков Windows",
        "command": "cleanmgr /sagerun:1", # Требует предварительной настройки профиля 1 или запуска cleanmgr без /sagerun для настройки
        "requires_admin": True
    },
    "Очистить диски (PowerShell) - TEMP": {
        "description": "Удаляет файлы из папки TEMP текущего пользователя и %WINDIR%\\Temp (требует админ)",
        "command": "Remove-Item -Path $env:TEMP\\*, $env:WINDIR\\Temp\\* -Recurse -Force -ErrorAction SilentlyContinue",
        "requires_admin": True
    },

    # --- Специфичные для PowerShell ---
    "Проверить версию PowerShell": {
        "description": "Отображает версию установленного PowerShell",
        "command": "$PSVersionTable"
    },
    "Получить список модулей PowerShell": {
        "description": "Список всех установленных модулей PowerShell",
        "command": "Get-Module -ListAvailable | Select-Object -Property Name, Version, Path | Sort-Object Name | Format-Table -AutoSize"
    },
    "Проверить Execution Policy": {
        "description": "Проверяет текущую политику выполнения скриптов PowerShell",
        "command": "Get-ExecutionPolicy -List"
    },
    "Установить Execution Policy (RemoteSigned)": {
        "description": "Устанавливает политику выполнения скриптов в RemoteSigned (требует админ)",
        "command": "Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser -Force",
        "requires_admin": True
    },

    "Проверить процесс по PID": {
        "description": "Показать информацию о процессе по его идентификатору (PID)",
        "template": "Get-Process -Id {input} -ErrorAction Stop | Select-Object -Property Name, Id, CPU, WorkingSet, Path | Format-List",
        "input_prompt": "Введите идентификатор процесса (PID)",
        "input_pattern": r"^\d+$", # Только цифры
        "input_example": "1234"
    }
}