import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import socket
import struct
import threading
import queue
import json
import os
import sys
import pyaudio
import numpy as np

# Константы
HOST_PORT = 5000
AUDIO_PORT = 5001
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100

class VoiceChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Voice Chat")
        self.root.geometry("500x400")
        self.root.resizable(True, True)
        
        # Переменные
        self.is_host = False
        self.connected = False
        self.client_socket = None
        self.audio_stream = None
        self.p = None
        self.muted = False
        self.running = True
        self.message_queue = queue.Queue()
        self.audio_queue = queue.Queue()
        
        # Создание интерфейса
        self.create_widgets()
        
        # Запуск обработки сообщений
        self.process_messages()
        
    def create_widgets(self):
        # Фрейм выбора режима
        mode_frame = ttk.LabelFrame(self.root, text="Режим работы", padding=10)
        mode_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.host_btn = ttk.Button(mode_frame, text="🖥️ Быть ХОСТОМ (сервер)", command=self.start_as_host)
        self.host_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        self.client_btn = ttk.Button(mode_frame, text="🔗 Подключиться к другу", command=self.show_connect_dialog)
        self.client_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        
        # Фрейм статуса
        self.status_frame = ttk.LabelFrame(self.root, text="Статус", padding=10)
        self.status_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.status_label = ttk.Label(self.status_frame, text="❌ Не подключено", foreground="red")
        self.status_label.pack(side=tk.LEFT)
        
        self.ip_label = ttk.Label(self.status_frame, text="", foreground="blue")
        self.ip_label.pack(side=tk.RIGHT)
        
        # Фрейм чата
        chat_frame = ttk.LabelFrame(self.root, text="Чат", padding=10)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.chat_display = scrolledtext.ScrolledText(chat_frame, height=10, state='disabled')
        self.chat_display.pack(fill=tk.BOTH, expand=True)
        
        # Фрейм ввода сообщения
        input_frame = ttk.Frame(chat_frame)
        input_frame.pack(fill=tk.X, pady=(5, 0))
        
        self.msg_entry = ttk.Entry(input_frame)
        self.msg_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        self.msg_entry.bind('<Return>', lambda e: self.send_message())
        
        send_btn = ttk.Button(input_frame, text="➤", command=self.send_message)
        send_btn.pack(side=tk.RIGHT, padx=(5, 0))
        
        # Фрейм управления голосом
        voice_frame = ttk.LabelFrame(self.root, text="Голосовая связь", padding=10)
        voice_frame.pack(fill=tk.X, padx=10, pady=5)
        
        self.mute_btn = ttk.Button(voice_frame, text="🎤 Мут (вкл)", command=self.toggle_mute)
        self.mute_btn.pack(side=tk.LEFT, padx=5, expand=True, fill=tk.X)
        self.mute_btn.state(['disabled'])
        
        self.disconnect_btn = ttk.Button(voice_frame, text="❌ Отключиться", command=self.disconnect)
        self.disconnect_btn.pack(side=tk.RIGHT, padx=5)
        self.disconnect_btn.state(['disabled'])
        
        # Индикатор голоса
        self.voice_indicator = ttk.Label(voice_frame, text="🔇", font=("Arial", 16))
        self.voice_indicator.pack(side=tk.RIGHT, padx=10)
        
    def get_local_ip(self):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            ip = s.getsockname()[0]
            s.close()
            return ip
        except:
            return "127.0.0.1"
    
    def start_as_host(self):
        self.is_host = True
        local_ip = self.get_local_ip()
        
        # Запуск сервера в отдельном потоке
        server_thread = threading.Thread(target=self.run_server, daemon=True)
        server_thread.start()
        
        self.status_label.config(text="✅ Ожидание подключения...", foreground="orange")
        self.ip_label.config(text=f"Ваш IP: {local_ip}:{HOST_PORT}")
        
        messagebox.showinfo("Хост запущен", 
                          f"Вы теперь хост!\n\n"
                          f"Ваш IP адрес: {local_ip}\n"
                          f"Порт: {HOST_PORT}\n\n"
                          f"Сообщите этот IP другу для подключения.\n"
                          f"Если друг в той же сети - используйте локальный IP.\n"
                          f"Если через интернет - нужен белый IP и проброс порта.")
        
        self.host_btn.state(['disabled'])
        self.client_btn.state(['disabled'])
        
    def run_server(self):
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind(('0.0.0.0', HOST_PORT))
        server_socket.listen(1)
        
        self.status_label.config(text="✅ Сервер запущен", foreground="green")
        
        try:
            self.client_socket, addr = server_socket.accept()
            self.connected = True
            
            self.root.after(0, lambda: self.on_connected(addr))
            
            # Обработка входящих данных
            while self.running and self.connected:
                try:
                    data_len = self.recv_exact(4)
                    if not data_len:
                        break
                    
                    length = struct.unpack('!I', data_len)[0]
                    data = self.recv_exact(length)
                    
                    if not data:
                        break
                    
                    msg = json.loads(data.decode('utf-8'))
                    self.message_queue.put(msg)
                    
                except:
                    break
                    
        except Exception as e:
            self.root.after(0, lambda: messagebox.showerror("Ошибка", f"Ошибка сервера: {str(e)}"))
        finally:
            server_socket.close()
            if self.connected:
                self.root.after(0, self.disconnect)
    
    def recv_exact(self, n):
        data = b''
        while len(data) < n and self.running and self.connected:
            try:
                chunk = self.client_socket.recv(n - len(data))
                if not chunk:
                    return None
                data += chunk
            except:
                return None
        return data if len(data) == n else None
    
    def show_connect_dialog(self):
        dialog = tk.Toplevel(self.root)
        dialog.title("Подключение")
        dialog.geometry("350x150")
        dialog.resizable(False, False)
        dialog.transient(self.root)
        dialog.grab_set()
        
        ttk.Label(dialog, text="IP адрес друга:").pack(pady=10)
        
        ip_entry = ttk.Entry(dialog, width=40)
        ip_entry.pack(padx=20)
        ip_entry.insert(0, self.get_local_ip().rsplit('.', 1)[0] + '.???')
        ip_entry.select_range(0, 'end')
        
        def connect():
            ip = ip_entry.get().strip()
            if ip:
                dialog.destroy()
                self.connect_to_host(ip)
        
        ttk.Button(dialog, text="Подключиться", command=connect).pack(pady=10)
        ip_entry.focus()
        ip_entry.select_range(0, 'end')
        
    def connect_to_host(self, host_ip):
        try:
            self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.settimeout(5)
            self.client_socket.connect((host_ip, HOST_PORT))
            self.client_socket.settimeout(None)
            
            self.connected = True
            self.on_connected((host_ip, HOST_PORT))
            
            # Поток приема данных
            recv_thread = threading.Thread(target=self.receive_data, daemon=True)
            recv_thread.start()
            
        except Exception as e:
            messagebox.showerror("Ошибка подключения", f"Не удалось подключиться к {host_ip}\n\n{str(e)}")
            self.disconnect()
    
    def on_connected(self, addr):
        self.connected = True
        self.status_label.config(text="✅ Подключено", foreground="green")
        self.ip_label.config(text=f"Собеседник: {addr[0]}")
        
        self.mute_btn.state(['!disabled'])
        self.disconnect_btn.state(['!disabled'])
        self.host_btn.state(['disabled'])
        self.client_btn.state(['disabled'])
        
        self.add_chat_message("SYSTEM", "Подключение установлено!")
        
        # Запуск аудиопотока
        self.start_audio()
    
    def receive_data(self):
        while self.running and self.connected:
            try:
                data_len = self.recv_exact(4)
                if not data_len:
                    break
                
                length = struct.unpack('!I', data_len)[0]
                data = self.recv_exact(length)
                
                if not data:
                    break
                
                msg = json.loads(data.decode('utf-8'))
                self.message_queue.put(msg)
                
            except:
                break
        
        if self.connected:
            self.root.after(0, self.disconnect)
    
    def process_messages(self):
        try:
            while True:
                msg = self.message_queue.get_nowait()
                
                if msg['type'] == 'chat':
                    self.add_chat_message(msg['user'], msg['text'])
                elif msg['type'] == 'audio':
                    self.play_audio(msg['data'])
                elif msg['type'] == 'system':
                    self.add_chat_message("SYSTEM", msg['text'])
                    
        except queue.Empty:
            pass
        
        if self.running:
            self.root.after(10, self.process_messages)
    
    def add_chat_message(self, user, text):
        self.chat_display.config(state='normal')
        timestamp = threading.current_thread().name[:4] if threading.current_thread().name != "MainThread" else ""
        self.chat_display.insert(tk.END, f"[{timestamp}] {user}: {text}\n")
        self.chat_display.see(tk.END)
        self.chat_display.config(state='disabled')
    
    def send_message(self):
        text = self.msg_entry.get().strip()
        if text and self.connected:
            msg = {
                'type': 'chat',
                'user': 'Host' if self.is_host else 'Client',
                'text': text
            }
            self.send_data(msg)
            self.msg_entry.delete(0, tk.END)
    
    def toggle_mute(self):
        self.muted = not self.muted
        if self.muted:
            self.mute_btn.config(text="🔇 Мут (выкл)")
            self.voice_indicator.config(text="🔇")
        else:
            self.mute_btn.config(text="🎤 Мут (вкл)")
            self.voice_indicator.config(text="🎤")
    
    def start_audio(self):
        try:
            self.p = pyaudio.PyAudio()
            
            # Поток записи
            def audio_callback(in_data, frame_count, time_info, status):
                if not self.muted and self.connected:
                    audio_data = np.frombuffer(in_data, dtype=np.int16)
                    # Сжатие данных (простое прореживание)
                    compressed = audio_data[::2].tobytes()
                    
                    msg = {
                        'type': 'audio',
                        'data': list(np.frombuffer(compressed, dtype=np.int16))
                    }
                    try:
                        self.send_data(msg)
                        self.root.after(0, lambda: self.voice_indicator.config(text="🎤"))
                    except:
                        pass
                else:
                    self.root.after(0, lambda: self.voice_indicator.config(text="🔇"))
                
                return (None, pyaudio.paContinue)
            
            self.audio_stream = self.p.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK,
                stream_callback=audio_callback
            )
            self.audio_stream.start_stream()
            
        except Exception as e:
            messagebox.showwarning("Предупреждение", f"Не удалось запустить аудио:\n{str(e)}\n\nЧат будет работать без голоса.")
    
    def play_audio(self, audio_data):
        try:
            if self.p and self.connected:
                # Восстановление данных
                restored = np.array(audio_data, dtype=np.int16)
                # Интерполяция
                expanded = np.zeros(len(restored) * 2, dtype=np.int16)
                expanded[::2] = restored
                expanded[1::2] = restored
                
                stream = self.p.open(
                    format=FORMAT,
                    channels=CHANNELS,
                    rate=RATE,
                    output=True,
                    frames_per_buffer=len(expanded)
                )
                stream.write(expanded.tobytes())
                stream.stop_stream()
                stream.close()
                
        except Exception as e:
            pass  # Тихо игнорируем ошибки воспроизведения
    
    def send_data(self, msg):
        if self.connected and self.client_socket:
            try:
                data = json.dumps(msg).encode('utf-8')
                self.client_socket.sendall(struct.pack('!I', len(data)) + data)
            except:
                self.disconnect()
    
    def disconnect(self):
        if not self.connected:
            return
        
        self.connected = False
        
        if self.audio_stream:
            self.audio_stream.stop_stream()
            self.audio_stream.close()
        
        if self.p:
            self.p.terminate()
        
        if self.client_socket:
            try:
                self.client_socket.close()
            except:
                pass
        
        self.status_label.config(text="❌ Отключено", foreground="red")
        self.ip_label.config(text="")
        self.mute_btn.state(['disabled'])
        self.disconnect_btn.state(['disabled'])
        self.host_btn.state(['!disabled'])
        self.client_btn.state(['!disabled'])
        self.voice_indicator.config(text="🔇")
        
        self.add_chat_message("SYSTEM", "Соединение разорвано")
    
    def on_closing(self):
        self.running = False
        self.disconnect()
        self.root.destroy()

def main():
    root = tk.Tk()
    app = VoiceChatApp(root)
    root.protocol("WM_DELETE_WINDOW", app.on_closing)
    root.mainloop()

if __name__ == "__main__":
    main()
