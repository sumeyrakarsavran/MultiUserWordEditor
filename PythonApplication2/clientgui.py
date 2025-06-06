import socket
import threading
import tkinter as tk
from tkinter import simpledialog, messagebox

HOST = 'localhost'
PORT = 12345

class ClientApp:
    def __init__(self, master):
        self.master = master
        self.master.title("Multi User Text Editor")

        self.text_area = tk.Text(master, undo=True)
        self.text_area.pack(expand=True, fill='both')

        self.text_area.bind("<KeyRelease>", self.on_text_change)

        self.username = simpledialog.askstring("Username", "Enter your name:", parent=self.master)
        if not self.username:
            self.master.destroy()
            return

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
        except:
            messagebox.showerror("Error", "Could not connect to server.")
            self.master.destroy()
            return

        self.running = True
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def on_text_change(self, event=None):
        content = self.text_area.get("1.0", "end-1c")
        try:
            message = f"{self.username}>>{content}\n"
            self.client_socket.sendall(message.encode("utf-8"))
        except:
            pass

    def receive_loop(self):
        buffer = ""
        while self.running:
            try:
                data = self.client_socket.recv(4096).decode("utf-8", errors="ignore")
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    full_msg, buffer = buffer.split("\n", 1)
                    if ">>" in full_msg:
                        sender, msg = full_msg.split(">>", 1)
                        if sender != self.username:
                            self.text_area.delete("1.0", "end")
                            self.text_area.insert("1.0", msg)
            except:
                break

    def on_close(self):
        self.running = False
        try:
            self.client_socket.close()
        except:
            pass
        self.mas
