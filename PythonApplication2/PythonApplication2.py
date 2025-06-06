import socket
import threading
import json
import os

HOST = '127.0.0.1'
PORT = 65432

clients = {}
files = {}  # {filename: content}

FILES_DIR = 'server_files'
os.makedirs(FILES_DIR, exist_ok=True)

def load_files():
    for fname in os.listdir(FILES_DIR):
        fpath = os.path.join(FILES_DIR, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            files[fname] = f.read()

def save_file(filename):
    fpath = os.path.join(FILES_DIR, filename)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(files[filename])

def broadcast(message, exclude_conn=None):
    for conn in clients.keys():
        if conn != exclude_conn:
            try:
                conn.sendall(message.encode('utf-8'))
            except:
                pass

def handle_client(conn, addr):
    print(f"{addr} connected.")
    clients[conn] = None  # username boş
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            msg = data.decode('utf-8')
            try:
                msg_json = json.loads(msg)
            except:
                continue

            action = msg_json.get('action')

            # Kullanıcı adı ayarla
            if action == 'set_username':
                username = msg_json.get('username')
                clients[conn] = username
                # Dosya listesini gönder
                files_list_msg = json.dumps({
                    'action': 'files_list',
                    'files': list(files.keys())
                })
                conn.sendall(files_list_msg.encode('utf-8'))

            # Yeni dosya oluştur
            elif action == 'create_file':
                filename = msg_json.get('filename')
                if filename not in files:
                    files[filename] = ""
                    save_file(filename)
                    # Tüm istemcilere yeni dosya bilgisini gönder
                    broadcast(json.dumps({
                        'action': 'file_created',
                        'filename': filename
                    }))

            # Dosya içeriği talebi
            elif action == 'open_file':
                filename = msg_json.get('filename')
                content = files.get(filename, "")
                conn.sendall(json.dumps({
                    'action': 'file_content',
                    'filename': filename,
                    'content': content
                }).encode('utf-8'))

            # Dosya içeriği güncelleme
            elif action == 'edit_file':
                filename = msg_json.get('filename')
                content = msg_json.get('content')
                files[filename] = content
                save_file(filename)
                # Güncellemeyi diğer istemcilere gönder (except gönderene)
                broadcast(json.dumps({
                    'action': 'file_update',
                    'filename': filename,
                    'content': content
                }), exclude_conn=conn)

    except Exception as e:
        print(f"Error with {addr}: {e}")
    finally:
        print(f"{addr} disconnected.")
        del clients[conn]
        conn.close()

def main():
    load_files()
    print(f"Loaded files: {list(files.keys())}")

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Server listening on {HOST}:{PORT}")

        while True:
            conn, addr = s.accept()
            threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()

if __name__ == "__main__":
    main()
