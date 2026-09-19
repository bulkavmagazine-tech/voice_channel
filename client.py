#!/usr/bin/env python3
"""
Voice Chat Client
Клиент для голосовой связи и чата
"""

import socketio
import pyaudio
import numpy as np
import threading
import sys
from tkinter import Tk, Label, Entry, Button, Text, Scrollbar, Frame, messagebox
from tkinter.ttk import Style

# Настройки аудио
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class VoiceChatClient:
    def __init__(self):
        self.sio = socketio.Client()
        self.audio = pyaudio.PyAudio()
        self.output_stream = None
        self.input_stream = None
        self.client_id = None
        self.is_muted = False
        self.root = None
        self.chat_display = None
        self.mute_btn = None
        self.setup_socket_events()
        
    def setup_socket_events(self):
        """Настройка событий сокета"""
        
        @self.sio.event
        def connect():
            print("Подключено к серверу!")
            if self.root:
                self.root.after(0, lambda: self.status_label.config(text="Статус: Подключено", fg="green"))
        
        @self.sio.event
        def disconnect():
            print("Отключено от сервера")
            if self.root:
                self.root.after(0, lambda: self.status_label.config(text="Статус: Отключено", fg="red"))
        
        @self.sio.on('voice_data')
        def on_voice_data(data):
            """Получение голосовых данных"""
            try:
                if self.output_stream and not self.is_muted:
                    self.output_stream.write(data)
            except Exception as e:
                print(f"Ошибка воспроизведения: {e}")
        
        @self.sio.on('chat_message')
        def on_chat_message(data):
            """Получение сообщения чата"""
            message = data.get('message', '')
            sender = data.get('sender', 'Аноним')
            if self.chat_display and self.root:
                self.root.after(0, lambda: self.chat_display.insert('end', f"{sender}: {message}\n"))
                self.root.after(0, lambda: self.chat_display.see('end'))
        
        @self.sio.on('joined')
        def on_joined(data):
            """Подтверждение присоединения"""
            print(f"Присоединился как {data.get('client_id')}")
    
    def start_audio_output(self):
        """Запуск потока вывода аудио"""
        try:
            self.output_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                output=True,
                frames_per_buffer=CHUNK
            )
        except Exception as e:
            print(f"Ошибка создания выходного потока: {e}")
    
    def start_audio_input(self):
        """Запуск потока ввода аудио (микрофон)"""
        try:
            self.input_stream = self.audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            def audio_sender():
                """Отправка аудио на сервер"""
                while True:
                    try:
                        if self.input_stream and not self.is_muted:
                            data = self.input_stream.read(CHUNK, exception_on_overflow=False)
                            self.sio.emit('voice_data', data)
                    except Exception as e:
                        print(f"Ошибка отправки аудио: {e}")
                        break
            
            thread = threading.Thread(target=audio_sender)
            thread.daemon = True
            thread.start()
        except Exception as e:
            print(f"Ошибка создания входного потока: {e}")
    
    def connect_to_server(self, server_ip):
        """Подключение к серверу"""
        try:
            self.sio.connect(f'http://{server_ip}:5000')
            self.client_id = self.sio.sid
            self.sio.emit('join', {'client_id': self.client_id})
            return True
        except Exception as e:
            print(f"Ошибка подключения: {e}")
            return False
    
    def send_chat_message(self, message):
        """Отправка сообщения чата"""
        if message.strip():
            self.sio.emit('chat_message', {
                'message': message,
                'sender': self.client_id[:8] if self.client_id else 'Аноним'
            })
    
    def disconnect(self):
        """Отключение от сервера"""
        if self.client_id:
            self.sio.emit('leave', {'client_id': self.client_id})
        self.sio.disconnect()
        if self.output_stream:
            self.output_stream.stop_stream()
            self.output_stream.close()
        if self.input_stream:
            self.input_stream.stop_stream()
            self.input_stream.close()
        self.audio.terminate()
    
    def toggle_mute(self):
        """Переключение режима mute"""
        self.is_muted = not self.is_muted
        if self.mute_btn and self.root:
            if self.is_muted:
                self.root.after(0, lambda: self.mute_btn.config(text="🔇 ВКЛЮЧИТЬ МИКРОФОН", bg="red"))
            else:
                self.root.after(0, lambda: self.mute_btn.config(text="🎤 ВЫКЛЮЧИТЬ МИКРОФОН", bg="lightgreen"))


class GUI:
    def __init__(self, root, client):
        self.root = root
        self.client = client
        self.client.root = root
        
        root.title("Voice Chat")
        root.geometry("500x600")
        root.resizable(True, True)
        
        # Стили
        style = Style()
        style.configure('TButton', font=('Arial', 10))
        
        # Фрейм подключения
        connect_frame = Frame(root, pady=10)
        connect_frame.pack(fill='x', padx=10)
        
        Label(connect_frame, text="IP сервера:", font=('Arial', 11)).pack(side='left')
        self.ip_entry = Entry(connect_frame, width=20, font=('Arial', 11))
        self.ip_entry.pack(side='left', padx=5)
        self.ip_entry.insert(0, '192.168.1.')  # Подсказка
        
        self.connect_btn = Button(connect_frame, text="Подключиться", 
                                  command=self.on_connect, bg='lightblue',
                                  font=('Arial', 10, 'bold'))
        self.connect_btn.pack(side='left', padx=5)
        
        # Статус
        self.status_label = Label(root, text="Статус: Отключено", 
                                  font=('Arial', 10), fg='red')
        self.status_label.pack(pady=5)
        
        # Чат
        chat_frame = Frame(root)
        chat_frame.pack(fill='both', expand=True, padx=10, pady=5)
        
        Label(chat_frame, text="Чат:", font=('Arial', 11, 'bold')).pack(anchor='w')
        
        # Поле сообщений
        message_frame = Frame(chat_frame)
        message_frame.pack(fill='both', expand=True)
        
        scrollbar = Scrollbar(message_frame)
        scrollbar.pack(side='right', fill='y')
        
        self.chat_display = Text(message_frame, wrap='word', yscrollcommand=scrollbar.set,
                                 font=('Consolas', 10), bg='#f0f0f0')
        self.chat_display.pack(side='left', fill='both', expand=True)
        scrollbar.config(command=self.chat_display.yview)
        
        self.client.chat_display = self.chat_display
        
        # Поле ввода сообщения
        input_frame = Frame(root)
        input_frame.pack(fill='x', padx=10, pady=5)
        
        self.message_entry = Entry(input_frame, font=('Arial', 11))
        self.message_entry.pack(side='left', fill='x', expand=True)
        self.message_entry.bind('<Return>', lambda e: self.send_message())
        
        send_btn = Button(input_frame, text="Отправить", command=self.send_message,
                          bg='lightgreen', font=('Arial', 10, 'bold'))
        send_btn.pack(side='left', padx=5)
        
        # Кнопки управления
        control_frame = Frame(root, pady=10)
        control_frame.pack(fill='x', padx=10)
        
        self.mute_btn = Button(control_frame, text="🎤 ВЫКЛЮЧИТЬ МИКРОФОН",
                               command=self.toggle_mute, bg='lightgreen',
                               font=('Arial', 11, 'bold'), height=2)
        self.mute_btn.pack(fill='x')
        self.client.mute_btn = self.mute_btn
        
        disconnect_btn = Button(control_frame, text="Отключиться",
                                command=self.on_disconnect, bg='salmon',
                                font=('Arial', 10))
        disconnect_btn.pack(fill='x', pady=5)
        
        # Инфо
        info_label = Label(root, text="Нажмите Ctrl+Q для быстрого выхода",
                          font=('Arial', 9), fg='gray')
        info_label.pack(pady=5)
    
    def on_connect(self):
        """Обработчик кнопки подключения"""
        ip = self.ip_entry.get().strip()
        if not ip:
            messagebox.showerror("Ошибка", "Введите IP адрес сервера")
            return
        
        self.connect_btn.config(state='disabled')
        self.ip_entry.config(state='disabled')
        
        # Запускаем подключение в потоке
        thread = threading.Thread(target=self.connect_thread, args=(ip,))
        thread.daemon = True
        thread.start()
    
    def connect_thread(self, ip):
        """Поток подключения"""
        success = self.client.connect_to_server(ip)
        if success:
            self.root.after(0, lambda: self.status_label.config(
                text="Статус: Подключено", fg="green"))
            self.root.after(0, self.client.start_audio_output)
            self.root.after(0, self.client.start_audio_input)
        else:
            self.root.after(0, lambda: messagebox.showerror(
                "Ошибка", "Не удалось подключиться к серверу"))
            self.root.after(0, lambda: self.connect_btn.config(state='normal'))
            self.root.after(0, lambda: self.ip_entry.config(state='normal'))
    
    def send_message(self):
        """Отправка сообщения"""
        message = self.message_entry.get().strip()
        if message:
            self.client.send_chat_message(message)
            self.message_entry.delete(0, 'end')
    
    def toggle_mute(self):
        """Переключение mute"""
        self.client.toggle_mute()
    
    def on_disconnect(self):
        """Отключение"""
        self.client.disconnect()
        self.status_label.config(text="Статус: Отключено", fg="red")
        self.connect_btn.config(state='normal')
        self.ip_entry.config(state='normal')
        self.chat_display.insert('end', "\n--- Отключено от сервера ---\n")


def main():
    print("=" * 50)
    print("Voice Chat Client")
    print("=" * 50)
    print("\nЗапуск графического интерфейса...\n")
    
    root = Tk()
    client = VoiceChatClient()
    gui = GUI(root, client)
    
    # Обработка закрытия окна
    def on_closing():
        client.disconnect()
        root.destroy()
        sys.exit(0)
    
    root.protocol("WM_DELETE_WINDOW", on_closing)
    
    # Горячая клавиша для выхода
    def check_quit(event=None):
        if event and event.keysym == 'q' and event.state & 0x4:  # Ctrl+Q
            on_closing()
    
    root.bind('<Control-q>', check_quit)
    
    root.mainloop()


if __name__ == '__main__':
    main()
