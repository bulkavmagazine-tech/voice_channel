#!/usr/bin/env python3
"""
Быстрый старт для Voice Chat
Запускает сервер или клиент в зависимости от аргумента
"""

import sys
import subprocess

def run_host():
    """Запустить сервер (хост)"""
    print("Запуск сервера...")
    subprocess.run([sys.executable, "host.py"])

def run_client():
    """Запустить клиент"""
    print("Запуск клиента...")
    subprocess.run([sys.executable, "client.py"])

def show_help():
    """Показать справку"""
    print("""
Использование:
  python run.py host    - Запустить сервер (хост)
  python run.py client  - Запустить клиент
  python run.py         - Запустить клиент (по умолчанию)

Примеры:
  python run.py host    # Вы будете хостом
  python run.py client  # Вы подключаетесь к другу
""")

if __name__ == '__main__':
    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        if command == 'host':
            run_host()
        elif command == 'client':
            run_client()
        else:
            show_help()
    else:
        # По умолчанию запускаем клиент
        run_client()
