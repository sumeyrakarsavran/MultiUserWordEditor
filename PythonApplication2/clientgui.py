# client_gui_customtkinter.py
import socket
import threading
import customtkinter as ctk
from tkinter import filedialog

HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 1024

class EditorApp:
    def __init__(self):
        self.sock = None
        self.username = ""
        self.filename = ""

        ctk.set_appearance_mode("light")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("Multiuser Editor")
        self.root.geometry("800x600")

        self.frame = ctk.CTkFrame(self.root)
        self.frame.pack(padx=10, pady=10, fill="both", expand=True)

        self.username_entry = ctk.CTkEntry(self.frame, placeholder_text="Username")
        self.username_entry.pack(pady=5)

        self.connect_button = ctk.CTkButton(self.frame, text="Connect", command=self.connect_to_server)
        self.connect_button.pack(pady=5)

        self.file_entry = ctk.CTkEntry(self.frame, placeholder_text="Dosya adi (ext yazma)")
        self.file_entry.pack(pady=5)

        self.open_button = ctk.CTkButton(self.frame, text="Dosya Ac", command=self.open_file)
        self.open_button.pack(pady=5)

        self.textbox = ctk.CTkTextbox(self.frame, wrap="word")
        self.textbox.pack(padx=10, pady=10, fill="both", expand=True)
        self.textbox.bind("<KeyRelease>", self.on_text_change)

        self.status_label = ctk.CTkLabel(self.frame, text="Durum: Bagli degil")
        self.status_label.pack(pady=5)

        self.last_content = ""

    def connect_to_server(self):
        try:
            self.username = self.username_entry.get().strip()
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.sock.connect((HOST, PORT))
            self.sock.sendall(self.username.encode('utf-8'))
            self.status_label.configure(text="Durum: Baglandi")
            threading.Thread(target=self.receive_data, daemon=True).start()
        except Exception as e:
            self.status_label.configure(text=f"Hata: {e}")

    def open_file(self):
        try:
            self.filename = self.file_entry.get().strip()
            if self.filename:
                self.sock.sendall(f"OPEN||{self.filename}".encode('utf-8'))
        except:
            pass

    def on_text_change(self, event=None):
        content = self.textbox.get("1.0", "end-1c")
        if content != self.last_content:
            self.last_content = content
            if self.filename:
                try:
                    self.sock.sendall(f"EDIT||{self.filename}||{content}".encode('utf-8'))
                except:
                    pass

    def receive_data(self):
        while True:
            try:
                data = self.sock.recv(BUFFER_SIZE).decode('utf-8')
                if not data:
                    break
                parts = data.split("||", 2)
                command = parts[0]
                if command == "LOAD":
                    _, fname, content = parts
                    self.root.after(0, lambda: self.textbox.delete("1.0", "end"))
                    self.root.after(0, lambda: self.textbox.insert("1.0", content))
                    self.last_content = content
                elif command == "UPDATE":
                    _, fname, content = parts
                    if fname == self.filename:
                        self.root.after(0, lambda: self.textbox.delete("1.0", "end"))
                        self.root.after(0, lambda: self.textbox.insert("1.0", content))
                        self.last_content = content
            except:
                break

    def run(self):
        self.root.mainloop()

if __name__ == "__main__":
    app = EditorApp()
    app.run()
