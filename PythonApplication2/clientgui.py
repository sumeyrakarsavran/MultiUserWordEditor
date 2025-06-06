import socket
import threading
import json
import tkinter as tk
import customtkinter as ctk

HOST = '127.0.0.1'
PORT = 65432

ctk.set_appearance_mode("System")
ctk.set_default_color_theme("blue")

class ClientApp(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Çok Kullanıcılı Metin Editörü")
        self.geometry("600x500")

        self.conn = None
        self.current_file = None
        self.username = "User"  # İstersen kullanıcı adını sabit bırak veya giriş ekle

        self.create_widgets()
        self.connect_to_server()

    def create_widgets(self):
        # Üst frame: Dosya oluşturma ve dosya adı girişi
        self.top_frame = ctk.CTkFrame(self)
        self.top_frame.pack(pady=10, padx=10, fill='x')

        self.filename_entry = ctk.CTkEntry(self.top_frame, placeholder_text="Yeni dosya adı giriniz")
        self.filename_entry.pack(side='left', padx=5)

        self.create_file_btn = ctk.CTkButton(self.top_frame, text="Dosya Oluştur", command=self.create_file)
        self.create_file_btn.pack(side='left', padx=5)

        # Dosya listesi için tkinter Listbox
        self.files_listbox = tk.Listbox(self, height=8)
        self.files_listbox.pack(padx=10, fill='x')
        self.files_listbox.bind("<<ListboxSelect>>", self.file_selected)

        # Metin editör, başta gizli
        self.text_editor = ctk.CTkTextbox(self, width=580, height=300)
        self.text_editor.pack(padx=10, pady=10)
        self.text_editor.pack_forget()
        self.text_editor.bind("<<Modified>>", self.text_modified)

    def connect_to_server(self):
        self.conn = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.conn.connect((HOST, PORT))
            # Kullanıcı adı gönder
            self.send_json({"action": "set_username", "username": self.username})

            # Server'dan gelenleri dinleyen thread
            threading.Thread(target=self.receive_loop, daemon=True).start()
        except Exception as e:
            print("Sunucuya bağlanılamadı:", e)

    def send_json(self, data):
        msg = json.dumps(data)
        self.conn.sendall(msg.encode('utf-8'))

    def receive_loop(self):
        buffer = ""
        while True:
            try:
                data = self.conn.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                # JSON ayrıştırması için basit yaklaşım (tek mesaj varsayılarak)
                while True:
                    try:
                        obj, index = json.JSONDecoder().raw_decode(buffer)
                        buffer = buffer[index:].lstrip()
                    except:
                        break
                    self.handle_message(obj)
            except Exception as e:
                print("Sunucu bağlantısı kesildi:", e)
                break

    def handle_message(self, msg):
        action = msg.get('action')
        if action == 'files_list':
            files = msg.get('files', [])
            self.update_file_list(files)
        elif action == 'file_created':
            filename = msg.get('filename')
            self.add_file_to_list(filename)
        elif action == 'file_content':
            filename = msg.get('filename')
            content = msg.get('content')
            if filename == self.current_file:
                self.show_text_editor(content)
        elif action == 'file_update':
            filename = msg.get('filename')
            content = msg.get('content')
            if filename == self.current_file:
                self.update_text_editor(content)

    def update_file_list(self, files):
        self.files_listbox.delete(0, tk.END)
        for f in files:
            self.files_listbox.insert(tk.END, f)

    def add_file_to_list(self, filename):
        self.files_listbox.insert(tk.END, filename)

    def create_file(self):
        filename = self.filename_entry.get().strip()
        if filename:
            self.send_json({"action": "create_file", "filename": filename})
            self.filename_entry.delete(0, tk.END)
            self.current_file = filename
            self.show_text_editor("")
        else:
            print("Dosya adı boş olamaz!")

    def file_selected(self, event):
        if not self.files_listbox.curselection():
            return
        index = self.files_listbox.curselection()[0]
        filename = self.files_listbox.get(index)
        self.current_file = filename
        self.send_json({"action": "open_file", "filename": filename})

    def show_text_editor(self, content):
        self.text_editor.pack(padx=10, pady=10)
        self.text_editor.delete("0.0", tk.END)
        self.text_editor.insert(tk.END, content)
        self.text_editor.edit_modified(False)

    def update_text_editor(self, content):
        # Güncelleme geldiğinde kullanıcı yazıyorsa çakışmasın diye kontrol yapabiliriz
        if not self.text_editor.edit_modified():
            self.text_editor.delete("0.0", tk.END)
            self.text_editor.insert(tk.END, content)
            self.text_editor.edit_modified(False)

    def text_modified(self, event):
        if self.text_editor.edit_modified():
            content = self.text_editor.get("0.0", tk.END)
            if self.current_file:
                self.send_json({"action": "edit_file", "filename": self.current_file, "content": content})
            self.text_editor.edit_modified(False)

if __name__ == "__main__":
    app = ClientApp()
    app.mainloop()
