import socket
import threading
import json
import customtkinter as ctk
from tkinter import messagebox, simpledialog

HOST = 'localhost'
PORT = 12345

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Realtime Collaborative Editor")
        self.root.geometry("800x600")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.username = simpledialog.askstring("Kullanıcı Adı", "Lütfen kullanıcı adınızı girin:", parent=self.root)
        if not self.username:
            messagebox.showerror("Hata", "Kullanıcı adı gereklidir.")
            root.destroy()
            return

        self.lock = threading.Lock()
        self.current_file = None
        self.files = []

        self.frame = ctk.CTkFrame(self.root)
        self.frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Sol tarafta dosya listesi ve yeni dosya oluşturma
        left_frame = ctk.CTkFrame(self.frame, width=200)
        left_frame.pack(side="left", fill="y", padx=(0,10), pady=5)

        ctk.CTkLabel(left_frame, text="Dosyalar").pack(pady=5)

        self.file_listbox = ctk.CTkTextbox(left_frame, height=300, state="disabled")
        self.file_listbox.pack(expand=True, fill="both", padx=5)

        self.file_listbox.bind("<1>", self.on_file_click)  # Mouse click handler

        # Yeni dosya oluşturma alanı
        ctk.CTkLabel(left_frame, text="Yeni Dosya Adı:").pack(pady=(10,0))
        self.new_file_entry = ctk.CTkEntry(left_frame)
        self.new_file_entry.pack(fill="x", padx=5, pady=5)
        self.create_file_btn = ctk.CTkButton(left_frame, text="Dosya Oluştur", command=self.create_file)
        self.create_file_btn.pack(padx=5)

        # Sağ tarafta metin kutusu ve kullanıcı listesi
        right_frame = ctk.CTkFrame(self.frame)
        right_frame.pack(side="right", expand=True, fill="both")

        self.textbox = ctk.CTkTextbox(right_frame)
        self.textbox.pack(expand=True, fill="both", padx=5, pady=(0,5))
        self.textbox.bind("<KeyRelease>", self.on_key_release)

        ctk.CTkLabel(right_frame, text="Bağlı Kullanıcılar:").pack(anchor="nw")
        self.user_listbox = ctk.CTkTextbox(right_frame, height=60, state="disabled")
        self.user_listbox.pack(fill="x", padx=5, pady=(0,10))

        # Socket bağlantısı
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
        except Exception as e:
            messagebox.showerror("Bağlantı Hatası", str(e))
            root.destroy()
            return

        # Sunucuya join mesajı gönder
        join_msg = json.dumps({"type": "join", "user": self.username})
        self.client_socket.sendall((join_msg + "\n").encode("utf-8"))

        self.running = True
        self.last_text = ""
        threading.Thread(target=self.receive_loop, daemon=True).start()

        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def update_file_listbox(self):
        self.file_listbox.configure(state="normal")
        self.file_listbox.delete("1.0", "end")
        for f in self.files:
            self.file_listbox.insert("end", f + "\n")
        self.file_listbox.configure(state="disabled")

    def on_file_click(self, event):
        # Tıklanan satırı bul
        index = self.file_listbox.index("@%d,%d linestart" % (event.x, event.y))
        line_num = int(index.split('.')[0])
        if line_num-1 < len(self.files):
            filename = self.files[line_num-1]
            self.open_file(filename)

    def create_file(self):
        filename = self.new_file_entry.get().strip()
        if not filename:
            messagebox.showwarning("Uyarı", "Dosya adı boş olamaz.")
            return
        if filename in self.files:
            messagebox.showwarning("Uyarı", "Bu isimde dosya zaten var.")
            return
        msg = json.dumps({"type": "create_file", "filename": filename})
        self.client_socket.sendall((msg + "\n").encode("utf-8"))
        self.new_file_entry.delete(0, "end")

    def open_file(self, filename):
        if filename == self.current_file:
            return
        self.current_file = filename
        msg = json.dumps({"type": "open_file", "filename": filename})
        self.client_socket.sendall((msg + "\n").encode("utf-8"))
        self.root.title(f"Realtime Collaborative Editor - {filename}")

    def on_key_release(self, event):
        with self.lock:
            if not self.current_file:
                return
            current_text = self.textbox.get("1.0", "end-1c")
            if current_text == self.last_text:
                return

            # Basit fark algılama: ekleme veya silme
            if len(current_text) < len(self.last_text):
                index = self.textbox.index("insert")
                msg = json.dumps({
                    "type": "delete",
                    "index": index,
                    "filename": self.current_file,
                    "user": self.username
                })
                self.client_socket.sendall((msg + "\n").encode("utf-8"))

            elif len(current_text) > len(self.last_text):
                inserted_text = current_text[len(self.last_text):]
                index = self.textbox.index(f"insert - {len(inserted_text)}c")
                msg = json.dumps({
                    "type": "insert",
                    "index": index,
                    "content": inserted_text,
                    "filename": self.current_file,
                    "user": self.username
                })
                self.client_socket.sendall((msg + "\n").encode("utf-8"))

            self.last_text = current_text

    def receive_loop(self):
        buffer = ""
        while self.running:
            try:
                data = self.client_socket.recv(1024).decode("utf-8")
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    msg_str, buffer = buffer.split("\n", 1)
                    self.handle_message(msg_str)
            except:
                break

    def handle_message(self, msg_str):
        try:
            msg = json.loads(msg_str)
            t = msg.get("type")

            if t == "files_list":
                self.files = msg.get("files", [])
                self.update_file_listbox()

            elif t == "file_created":
                filename = msg.get("filename")
                if filename and filename not in self.files:
                    self.files.append(filename)
                    self.update_file_listbox()

            elif t == "file_content":
                filename = msg.get("filename")
                content = msg.get("content", "")
                if filename == self.current_file:
                    with self.lock:
                        self.textbox.delete("1.0", "end")
                        self.textbox.insert("1.0", content)
                        self.last_text = content

            elif t == "insert":
                filename = msg.get("filename")
                if filename == self.current_file:
                    with self.lock:
                        idx = msg["index"]
                        content = msg["content"]
                        self.textbox.insert(idx, content)
                        self.last_text = self.textbox.get("1.0", "end-1c")

            elif t == "delete":
                filename = msg.get("filename")
                if filename == self.current_file:
                    with self.lock:
                        idx = msg["index"]
                        self.textbox.delete(idx)
                        self.last_text = self.textbox.get("1.0", "end-1c")

            elif t == "user_list":
                users = msg.get("content", [])
                self.user_listbox.configure(state="normal")
                self.user_listbox.delete("1.0", "end")
                for u in users:
                    self.user_listbox.insert("end", u + "\n")
                self.user_listbox.configure(state="disabled")

        except Exception as e:
            print(f"[CLIENT] Hata handle_message: {e}")

    def on_close(self):
        self.running = False
        try:
            self.client_socket.close()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = ClientApp(root)
    root.mainloop()
