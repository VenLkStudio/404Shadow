import sys
from libs.byedpi import main

# Устанавливаем аргументы командной строки
sys.argv = [
    'script.py',
    '-i', '0.0.0.0',
    '-p', '8080',
    '-f', '10',  # Позиция для фейкового пакета
    '-t', '8',   # TTL для фейковых пакетов
    '-x', '1'    # Уровень отладки
]

# Запускаем main
main()