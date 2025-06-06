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
        self.root.geometry("700x500")
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        # Kullanıcı adı sor
        self.username = simpledialog.askstring("Kullanıcı Adı", "Lütfen kullanıcı adınızı girin:", parent=self.root)
        if not self.username:
            messagebox.showerror("Hata", "Kullanıcı adı gereklidir.")
            root.destroy()
            return

        self.color = None
        self.lock = threading.Lock()

        # Frame
        self.frame = ctk.CTkFrame(self.root)
        self.frame.pack(expand=True, fill="both", padx=10, pady=10)

        # Kullanıcı listesi label
        self.user_list_label = ctk.CTkLabel(self.frame, text="Bağlı Kullanıcılar:")
        self.user_list_label.pack(anchor="nw")

        self.user_listbox = ctk.CTkTextbox(self.frame, height=50, state="disabled")
        self.user_listbox.pack(fill="x", padx=5, pady=(0,10))

        # Metin kutusu
        self.textbox = ctk.CTkTextbox(self.frame)
        self.textbox.pack(expand=True, fill="both")
        self.textbox.bind("<<Paste>>", self.on_paste)
        self.textbox.bind("<KeyRelease>", self.on_key_release)

        # Socket ayarları
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

    def on_paste(self, event):
        # Clipboard içeriği metin kutusuna zaten geliyor, ek işlem gerekmez
        pass

    def on_key_release(self, event):
        with self.lock:
            current_text = self.textbox.get("1.0", "end-1c")
            # Fark var mı kontrolü
            if current_text == self.last_text:
                return
            # Basit fark yakalama (ekleme ve silme)
            # Daha gelişmiş metin farkı için özel algoritma lazım
            # Burada sadece sondan farkı yakalıyoruz

            # Silme
            if len(current_text) < len(self.last_text):
                index = self.textbox.index("insert")
                msg = json.dumps({"type": "delete", "index": index, "user": self.username})
                self.client_socket.sendall((msg + "\n").encode("utf-8"))

            # Ekleme
            elif len(current_text) > len(self.last_text):
                inserted_text = current_text[len(self.last_text):]
                index = self.textbox.index(f"insert - {len(inserted_text)}c")
                msg = json.dumps({"type": "insert", "index": index, "content": inserted_text, "user": self.username})
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
            if t == "full_text":
                with self.lock:
                    self.textbox.delete("1.0", "end")
                    self.textbox.insert("1.0", msg["content"])
                    self.last_text = msg["content"]

            elif t == "insert":
                with self.lock:
                    idx = msg["index"]
                    content = msg["content"]
                    self.textbox.insert(idx, content)
                    self.last_text = self.textbox.get("1.0", "end-1c")

            elif t == "delete":
                with self.lock:
                    idx = msg["index"]
                    self.textbox.delete(idx)
                    self.last_text = self.textbox.get("1.0", "end-1c")

            elif t == "user_list":
                users = msg["content"]
                self.user_listbox.configure(state="normal")
                self.user_listbox.delete("1.0", "end")
                for u in users:
                    self.user_listbox.insert("end", f"{u}\n")
                self.user_listbox.configure(state="disabled")

        except Exception as e:
            print(f"[CLIENT] Error in handle_message: {e}")

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
