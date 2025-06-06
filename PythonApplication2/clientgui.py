import socket
import threading
import json
import tkinter as tk
from tkinter import simpledialog, messagebox

HOST = '127.0.0.1'
PORT = 65432

class ClientApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Real-time Collaborative Editor")

        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.sock.connect((HOST, PORT))

        self.username = None
        self.current_file = None
        self.files = []

        self.text_modified_by_me = False  # flag to prevent feedback loop

        # UI components
        self.frame = tk.Frame(root)
        self.frame.pack(fill=tk.BOTH, expand=True)

        self.listbox_files = tk.Listbox(self.frame, width=30)
        self.listbox_files.pack(side=tk.LEFT, fill=tk.Y)
        self.listbox_files.bind("<<ListboxSelect>>", self.on_file_select)

        btn_frame = tk.Frame(self.frame)
        btn_frame.pack(side=tk.LEFT, fill=tk.Y, padx=5)

        self.btn_create = tk.Button(btn_frame, text="Create File", command=self.create_file)
        self.btn_create.pack(pady=5)

        self.btn_refresh = tk.Button(btn_frame, text="Refresh Files", command=self.request_files)
        self.btn_refresh.pack(pady=5)

        self.text = tk.Text(self.frame, undo=True, wrap=tk.NONE)
        self.text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self.text.bind("<<Modified>>", self.on_text_modified)

        self.start_recv_thread()
        self.ask_username()

    def ask_username(self):
        username = simpledialog.askstring("Username", "Enter your username:", parent=self.root)
        if not username:
            messagebox.showerror("Error", "Username required.")
            self.root.destroy()
            return
        self.username = username
        self.send({
            "action": "set_username",
            "username": self.username
        })

    def send(self, data):
        try:
            msg = json.dumps(data) + "\n"
            self.sock.sendall(msg.encode('utf-8'))
        except Exception as e:
            print(f"Send error: {e}")

    def request_files(self):
        # Server sends files list on set_username, but we can force refresh if needed
        self.send({"action": "list_files"})

    def create_file(self):
        fname = simpledialog.askstring("Create File", "Enter new file name:", parent=self.root)
        if not fname:
            return
        self.send({"action": "create_file", "filename": fname})

    def on_file_select(self, event):
        selection = self.listbox_files.curselection()
        if not selection:
            return
        index = selection[0]
        filename = self.listbox_files.get(index)
        self.current_file = filename
        self.send({"action": "open_file", "filename": filename})

    def on_text_modified(self, event):
        if self.text_modified_by_me:
            # This change is from incoming server data, ignore to prevent loop
            self.text.edit_modified(False)
            return

        if not self.current_file:
            self.text.edit_modified(False)
            return

        # Get current cursor position
        try:
            index = self.text.index(tk.INSERT)
        except Exception:
            index = "1.0"

        # Get the content of the text widget
        # To detect insert/delete, we need to compare previous content and current content,
        # but for simplicity, we assume single character insert or delete here.

        # This is a simple heuristic:
        # On modification event, get the change by comparing previous snapshot and current text
        # But since Tkinter doesn't give direct diffs, we'll just send the whole content for now.
        # (For full operational transformation, a diffing lib or more complex logic is needed.)

        # Instead, here we detect whether the last key was an insert or delete:
        # Unfortunately Tkinter event doesn't give that directly.
        # So as a quick demo, let's send the whole content as "replace" operation.
        # But this breaks your insert/delete messaging protocol.
        # To keep your protocol, let's track last text snapshot and find difference.

        # So implement simple diff with last content:
        new_text = self.text.get("1.0", tk.END)[:-1]  # remove trailing newline
        old_text = getattr(self, 'last_text', '')
        self.last_text = new_text

        # Find first difference
        i = 0
        while i < len(new_text) and i < len(old_text) and new_text[i] == old_text[i]:
            i += 1

        if len(new_text) > len(old_text):
            # Insert happened
            inserted_text = new_text[i:len(new_text)-(len(old_text)-i)]
            # Compose index in "line.char" form
            line, char = map(int, self.text.index(f"1.0 + {i} chars").split('.'))
            index_str = f"{line}.{char}"
            self.send({
                "action": "insert",
                "filename": self.current_file,
                "index": index_str,
                "content": inserted_text
            })

        elif len(new_text) < len(old_text):
            # Delete happened
            # We assume one character deleted for simplicity
            line, char = map(int, self.text.index(f"1.0 + {i+1} chars").split('.'))
            index_str = f"{line}.{char}"
            self.send({
                "action": "delete",
                "filename": self.current_file,
                "index": index_str
            })

        self.text.edit_modified(False)

    def start_recv_thread(self):
        threading.Thread(target=self.recv_loop, daemon=True).start()

    def recv_loop(self):
        buffer = ""
        while True:
            try:
                data = self.sock.recv(4096)
                if not data:
                    break
                buffer += data.decode('utf-8')
                while "\n" in buffer:
                    msg_str, buffer = buffer.split("\n", 1)
                    self.handle_message(msg_str)
            except Exception as e:
                print(f"Receive error: {e}")
                break
        print("Disconnected from server")
        self.sock.close()

    def handle_message(self, msg_str):
        try:
            msg = json.loads(msg_str)
        except:
            return

        action = msg.get("action")

        if action == "files_list":
            self.files = msg.get("files", [])
            self.update_file_list()

        elif action == "file_created":
            fname = msg.get("filename")
            if fname and fname not in self.files:
                self.files.append(fname)
                self.update_file_list()

        elif action == "file_content":
            fname = msg.get("filename")
            content = msg.get("content", "")
            if fname == self.current_file:
                self.apply_full_content(content)

        elif action == "insert":
            fname = msg.get("filename")
            index = msg.get("index")
            content = msg.get("content")
            if fname == self.current_file and content:
                self.apply_insert(index, content)

        elif action == "delete":
            fname = msg.get("filename")
            index = msg.get("index")
            if fname == self.current_file:
                self.apply_delete(index)

    def update_file_list(self):
        self.listbox_files.delete(0, tk.END)
        for f in self.files:
            self.listbox_files.insert(tk.END, f)

    def apply_full_content(self, content):
        self.text_modified_by_me = True
        self.text.delete("1.0", tk.END)
        self.text.insert("1.0", content)
        self.text_modified_by_me = False
        self.last_text = content

    def apply_insert(self, index, content):
        self.text_modified_by_me = True
        try:
            self.text.insert(index, content)
            self.last_text = self.text.get("1.0", tk.END)[:-1]
        except:
            pass
        self.text_modified_by_me = False

    def apply_delete(self, index):
        self.text_modified_by_me = True
        try:
            # delete character before index (since server delete is index of char to delete)
            line, char = map(int, index.split('.'))
            if char > 0:
                start = f"{line}.{char - 1}"
                end = index
                self.text.delete(start, end)
                self.last_text = self.text.get("1.0", tk.END)[:-1]
        except:
            pass
        self.text_modified_by_me = False

if __name__ == "__main__":
    root = tk.Tk()
    app = ClientApp(root)
    root.mainloop()
