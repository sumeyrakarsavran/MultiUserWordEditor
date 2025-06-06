import socket
import threading
import customtkinter as ctk
from tkinter import simpledialog, messagebox

HOST = 'localhost'
PORT = 12345

class ClientApp:
    def __init__(self, root):
        self.root = root
        print("[INFO] GUI initialized")
        self.root.title("Modern Multi User Text Editor")
        self.root.geometry("600x400")

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.frame = ctk.CTkFrame(master=self.root)
        self.frame.pack(padx=20, pady=20, expand=True, fill="both")

        self.textbox = ctk.CTkTextbox(master=self.frame, corner_radius=10)
        self.textbox.pack(expand=True, fill="both", padx=10, pady=10)
        self.textbox.bind("<KeyRelease>", self.on_text_change)

        self.username = simpledialog.askstring("Username", "Enter your name:", parent=self.root)
        if not self.username:
            print("[WARN] No username entered, exiting.")
            self.root.destroy()
            return

        # Connect to server
        print("[INFO] Trying to connect to server...")
        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.client_socket.connect((HOST, PORT))
            print("[INFO] Connected to server.")
        except Exception as e:
            print(f"[ERROR] Connection failed: {e}")
            messagebox.showerror("Error", "Could not connect to the server.")
            self.root.destroy()
            return

        self.running = True
        threading.Thread(target=self.receive_loop, daemon=True).start()

    def on_text_change(self, event=None):
        content = self.textbox.get("1.0", "end-1c")
        try:
            msg = f"{self.username}>>{content}\n"
            self.client_socket.sendall(msg.encode("utf-8"))
        except Exception as e:
            print(f"[ERROR] Sending failed: {e}")

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
                            self.textbox.delete("1.0", "end")
                            self.textbox.insert("1.0", msg)
            except Exception as e:
                print(f"[ERROR] Receiving failed: {e}")
                break

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
    root.protocol("WM_DELETE_WINDOW", app.on_close)
    root.mainloop()
