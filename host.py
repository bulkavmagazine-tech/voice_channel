#!/usr/bin/env python3
"""
Voice Chat Server (Host)
Сервер для голосовой связи и чата
"""

import socket
import threading
import json
import pyaudio
import numpy as np
from flask import Flask
from flask_socketio import SocketIO, emit, join_room, leave_room
from flask_socketio import request
import sys

# Настройки аудио
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

# Глобальные переменные
audio = pyaudio.PyAudio()
clients = {}
voice_clients = {}

app = Flask(__name__)
app.config['SECRET_KEY'] = 'voice-chat-secret'
socketio = SocketIO(app, cors_allowed_origins="*")

def get_local_ip():
    """Получить локальный IP адрес"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def audio_listener(client_id):
    """Слушает микрофон и отправляет аудио клиенту"""
    stream = audio.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    try:
        while client_id in voice_clients:
            data = stream.read(CHUNK, exception_on_overflow=False)
            # Отправляем аудио всем подключенным клиентам кроме отправителя
            for cid, sid in list(clients.items()):
                if cid != client_id:
                    socketio.emit('voice_data', data, room=sid)
    except Exception as e:
        print(f"Ошибка аудио потока: {e}")
    finally:
        stream.stop_stream()
        stream.close()

@socketio.on('connect')
def handle_connect():
    """Обработка подключения клиента"""
    print(f"Клиент подключился: {request.sid}")

@socketio.on('join')
def handle_join(data):
    """Обработка присоединения к комнате"""
    client_id = data.get('client_id', request.sid)
    join_room(client_id)
    clients[client_id] = request.sid
    voice_clients[client_id] = True
    
    # Запускаем поток для прослушивания микрофона
    thread = threading.Thread(target=audio_listener, args=(client_id,))
    thread.daemon = True
    thread.start()
    
    emit('joined', {'client_id': client_id})
    print(f"Клиент {client_id} присоединился")

@socketio.on('leave')
def handle_leave(data):
    """Обработка выхода из комнаты"""
    client_id = data.get('client_id')
    if client_id in clients:
        leave_room(clients[client_id])
        del clients[client_id]
    if client_id in voice_clients:
        del voice_clients[client_id]
    print(f"Клиент {client_id} вышел")

@socketio.on('chat_message')
def handle_chat(data):
    """Обработка сообщения чата"""
    message = data.get('message', '')
    sender = data.get('sender', 'Аноним')
    
    # Отправляем сообщение всем клиентам
    emit('chat_message', {
        'message': message,
        'sender': sender
    }, broadcast=True)

@socketio.on('disconnect')
def handle_disconnect():
    """Обработка отключения клиента"""
    # Находим client_id по sid
    client_id = None
    for cid, sid in list(clients.items()):
        if sid == request.sid:
            client_id = cid
            break
    
    if client_id:
        if client_id in clients:
            del clients[client_id]
        if client_id in voice_clients:
            del voice_clients[client_id]
        print(f"Клиент {client_id} отключился")

if __name__ == '__main__':
    print("=" * 50)
    print("Voice Chat Server (Хост)")
    print("=" * 50)
    
    local_ip = get_local_ip()
    print(f"\nВаш IP адрес: {local_ip}")
    print(f"Сообщите этот IP другу для подключения\n")
    print("Сервер запущен. Нажмите Ctrl+C для остановки.\n")
    
    try:
        socketio.run(app, host='0.0.0.0', port=5000, debug=False)
    except KeyboardInterrupt:
        print("\nОстановка сервера...")
        audio.terminate()
        sys.exit(0)
