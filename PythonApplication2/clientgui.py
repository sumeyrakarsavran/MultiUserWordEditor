import socket
import threading
import customtkinter as ctk
from tkinter import messagebox

HOST = 'localhost'
PORT = 12345

class RealtimeEditorClient:
    def __init__(self, root):
        self.root = root
        self.root.title("Realtime Editor")
        self.root.geometry("600x400")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.frame = ctk.CTkFrame(self.root)
        self.frame.pack(expand=True, fill="both", padx=10, pady=10)

        self.textbox = ctk.CTkTextbox(self.frame)
        self.textbox.pack(expand=True, fill="both")
        self.textbox.bind("<KeyPress>", self.on_key_press)
        self.textbox.bind("<KeyRelease>", self.on_key_release)

        self.last_content = ""
        self.lock = threading.Lock()

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
        except Exception as e:
            messagebox.showerror("Connection Failed", str(e))
            self.root.destroy()
            return

        self.running = True
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def on_key_press(self, event):
        self.last_content = self.textbox.get("1.0", "end-1c")

    def on_key_release(self, event):
        new_content = self.textbox.get("1.0", "end-1c")
        with self.lock:
            if len(new_content) > len(self.last_content):
                added = new_content[len(self.last_content):]
                index = self.textbox.index("insert -1c")
                msg = f"insert|{index}|{added}"
                self.send_message(msg)
            elif len(new_content) < len(self.last_content):
                index = self.textbox.index("insert")
                msg = f"delete|{index}"
                self.send_message(msg)

    def send_message(self, msg):
        try:
            self.client_socket.sendall((msg + "\n").encode("utf-8"))
        except Exception as e:
            print(f"[ERROR] Sending message failed: {e}")

    def receive_loop(self):
        buffer = ""
        while self.running:
            try:
                data = self.client_socket.recv(1024).decode("utf-8")
                if not data:
                    break
                buffer += data
                while "\n" in buffer:
                    full_msg, buffer = buffer.split("\n", 1)
                    self.apply_change(full_msg)
            except:
                break

    def apply_change(self, msg):
        try:
            parts = msg.split("|")
            if parts[0] == "insert":
                index, content = parts[1], parts[2]
                self.textbox.insert(index, content)
            elif parts[0] == "delete":
                index = parts[1]
                self.textbox.delete(index)
        except Exception as e:
            print(f"[ERROR] Apply change failed: {e}")

    def on_close(self):
        self.running = False
        try:
            self.client_socket.close()
        except:
            pass
        self.root.destroy()

if __name__ == "__main__":
    root = ctk.CTk()
    app = RealtimeEditorClient(root)
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
