import socket
import threading
import json
import os
import time

HOST = 'localhost'
PORT = 12345

clients = {}  # client_socket: {"username":..., "color":..., "current_file": ...}
client_sockets = []
lock = threading.Lock()

FILES_DIR = "server_files"
os.makedirs(FILES_DIR, exist_ok=True)

# Dosyalar {filename: content}
files_content = {}

USER_COLORS = ["#FF4500", "#008000", "#0000FF", "#800080", "#FFA500"]

def broadcast(message, exclude=None):
    with lock:
        for client in client_sockets:
            if client != exclude:
                try:
                    client.sendall((message + "\n").encode('utf-8'))
                except:
                    pass

def send_user_list():
    user_list = [info["username"] for info in clients.values()]
    msg = json.dumps({"type": "user_list", "content": user_list})
    broadcast(msg)

def save_file(filename):
    path = os.path.join(FILES_DIR, filename)
    with open(path, "w", encoding="utf-8") as f:
        f.write(files_content.get(filename, ""))

def load_files():
    for fname in os.listdir(FILES_DIR):
        fpath = os.path.join(FILES_DIR, fname)
        with open(fpath, "r", encoding="utf-8") as f:
            files_content[fname] = f.read()

def send_file_list(client_socket):
    with lock:
        msg = json.dumps({"type": "files_list", "files": list(files_content.keys())})
        client_socket.sendall((msg + "\n").encode("utf-8"))

def handle_client(client_socket):
    global files_content

    buffer = ""
    user = None
    color = None

    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break
            buffer += data
            while "\n" in buffer:
                msg_str, buffer = buffer.split("\n", 1)
                msg = json.loads(msg_str)

                t = msg.get("type")

                if t == "join":
                    user = msg["user"]
                    with lock:
                        clients[client_socket] = {"username": user, "current_file": None}
                        client_sockets.append(client_socket)
                        color = USER_COLORS[len(client_sockets) % len(USER_COLORS)]
                        clients[client_socket]["color"] = color
                    print(f"[SERVER] {user} joined with color {color}")
                    # Dosya listesini gönder
                    send_file_list(client_socket)
                    # Kullanıcı listesi
                    send_user_list()
                    continue

                elif t == "create_file":
                    filename = msg.get("filename")
                    if not filename:
                        continue
                    with lock:
                        if filename not in files_content:
                            files_content[filename] = ""
                            save_file(filename)
                            # Yeni dosya bilgisini herkese gönder
                            broadcast(json.dumps({"type": "file_created", "filename": filename}))
                    continue

                elif t == "open_file":
                    filename = msg.get("filename")
                    with lock:
                        if filename in files_content:
                            clients[client_socket]["current_file"] = filename
                            content = files_content[filename]
                            # Dosya içeriğini gönder
                            client_socket.sendall(json.dumps({
                                "type": "file_content",
                                "filename": filename,
                                "content": content
                            }) .encode("utf-8") + b"\n")
                    continue

                elif t == "insert":
                    with lock:
                        current_file = clients.get(client_socket, {}).get("current_file")
                        if not current_file:
                            continue
                        if current_file != msg.get("filename"):
                            # Yanlış dosya güncellemesi, atla
                            continue

                        idx = msg["index"]
                        content_to_insert = msg["content"]
                        old_text = files_content[current_file]
                        new_text = insert_text(old_text, idx, content_to_insert)
                        files_content[current_file] = new_text
                        save_file(current_file)
                        # Güncellemeyi sadece o dosyayı açanlara gönder
                        for c, info in clients.items():
                            if info.get("current_file") == current_file and c != client_socket:
                                try:
                                    c.sendall((msg_str + "\n").encode("utf-8"))
                                except:
                                    pass

                elif t == "delete":
                    with lock:
                        current_file = clients.get(client_socket, {}).get("current_file")
                        if not current_file:
                            continue
                        if current_file != msg.get("filename"):
                            continue

                        idx = msg["index"]
                        old_text = files_content[current_file]
                        new_text = delete_text(old_text, idx)
                        files_content[current_file] = new_text
                        save_file(current_file)
                        # Güncellemeyi sadece o dosyayı açanlara gönder
                        for c, info in clients.items():
                            if info.get("current_file") == current_file and c != client_socket:
                                try:
                                    c.sendall((msg_str + "\n").encode("utf-8"))
                                except:
                                    pass

        except Exception as e:
            print(f"[SERVER] Error: {e}")
            break

    with lock:
        if client_socket in client_sockets:
            client_sockets.remove(client_socket)
        if client_socket in clients:
            left_user = clients[client_socket]["username"]
            print(f"[SERVER] {left_user} disconnected.")
            del clients[client_socket]
            send_user_list()
    client_socket.close()

def insert_text(text, index, content):
    try:
        line, char = map(int, index.split('.'))
        lines = text.split('\n')
        if line-1 < len(lines):
            line_text = lines[line-1]
            new_line_text = line_text[:char] + content + line_text[char:]
            lines[line-1] = new_line_text
            return '\n'.join(lines)
        else:
            return text + content
    except:
        return text + content

def delete_text(text, index):
    try:
        line, char = map(int, index.split('.'))
        lines = text.split('\n')
        if line-1 < len(lines):
            line_text = lines[line-1]
            if char > 0:
                new_line_text = line_text[:char-1] + line_text[char:]
                lines[line-1] = new_line_text
                return '\n'.join(lines)
        return text
    except:
        return text

def autosave_loop():
    while True:
        time.sleep(10)
        with lock:
            for fname in files_content:
                save_file(fname)
        print("[SERVER] Autosave completed.")

def start_server():
    load_files()
    print(f"[SERVER] Loaded files: {list(files_content.keys())}")

    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[SERVER] Listening on {HOST}:{PORT}")

    threading.Thread(target=autosave_loop, daemon=True).start()

    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(f"[SERVER] Connection from {addr}")
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        server_socket.close()
        print("[SERVER] Server closed.")

if __name__ == "__main__":
    start_server()
