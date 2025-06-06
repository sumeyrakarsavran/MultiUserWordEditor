import socket
import threading
import json
import time

HOST = 'localhost'
PORT = 12345

clients = {}  # client_socket: {"username":..., "color":...}
client_sockets = []
lock = threading.Lock()

# Dosya içeriği
document_text = ""

# Kullanıcı renkleri
USER_COLORS = ["#FF4500", "#008000", "#0000FF", "#800080", "#FFA500"]

def broadcast(message, exclude=None):
    with lock:
        for client in client_sockets:
            if client != exclude:
                try:
                    client.sendall((message + "\n").encode('utf-8'))
                except:
                    pass

def save_to_file():
    with open("shared_document.txt", "w", encoding="utf-8") as f:
        f.write(document_text)
    print("[SERVER] Document saved.")

def handle_client(client_socket):
    global document_text

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

                if msg["type"] == "join":
                    user = msg["user"]
                    with lock:
                        clients[client_socket] = {"username": user}
                        client_sockets.append(client_socket)
                        color = USER_COLORS[len(client_sockets) % len(USER_COLORS)]
                        clients[client_socket]["color"] = color
                    print(f"[SERVER] {user} joined with color {color}")
                    # Yeni kullanıcıya tam belgeyi gönderelim
                    full_text_msg = json.dumps({
                        "type": "full_text",
                        "content": document_text
                    })
                    client_socket.sendall((full_text_msg + "\n").encode('utf-8'))
                    # Herkese kullanıcı listesini gönder
                    send_user_list()
                    continue

                if msg["type"] == "insert":
                    idx = msg["index"]
                    content = msg["content"]
                    # Basit şekilde ekleme (daha gelişmiş için index parse etmek gerek)
                    document_text = insert_text(document_text, idx, content)
                    broadcast(msg_str, exclude=client_socket)

                elif msg["type"] == "delete":
                    idx = msg["index"]
                    # Basit şekilde 1 karakter sil
                    document_text = delete_text(document_text, idx)
                    broadcast(msg_str, exclude=client_socket)

        except Exception as e:
            print(f"[SERVER] Error: {e}")
            break

    # Client çıktı, temizle
    with lock:
        if client_socket in client_sockets:
            client_sockets.remove(client_socket)
        if client_socket in clients:
            left_user = clients[client_socket]["username"]
            print(f"[SERVER] {left_user} disconnected.")
            del clients[client_socket]
            send_user_list()
    client_socket.close()

def send_user_list():
    user_list = [info["username"] for info in clients.values()]
    msg = json.dumps({"type": "user_list", "content": user_list})
    broadcast(msg)

def insert_text(text, index, content):
    # index = "line.char"
    try:
        line, char = map(int, index.split('.'))
        lines = text.split('\n')
        if line-1 < len(lines):
            line_text = lines[line-1]
            new_line_text = line_text[:char] + content + line_text[char:]
            lines[line-1] = new_line_text
            return '\n'.join(lines)
        else:
            # Satır yoksa ekle sonuna
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
            save_to_file()

def start_server():
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
