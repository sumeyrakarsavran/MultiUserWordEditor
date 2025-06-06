import socket
import threading
import json
import os

HOST = '127.0.0.1'
PORT = 65432

clients = {}  # conn: {"username":..., "current_file":...}
files = {}  # filename: content

FILES_DIR = 'server_files'
os.makedirs(FILES_DIR, exist_ok=True)
lock = threading.Lock()

def load_files():
    for fname in os.listdir(FILES_DIR):
        fpath = os.path.join(FILES_DIR, fname)
        with open(fpath, 'r', encoding='utf-8') as f:
            files[fname] = f.read()

def save_file(filename):
    fpath = os.path.join(FILES_DIR, filename)
    with open(fpath, 'w', encoding='utf-8') as f:
        f.write(files[filename])

def broadcast_to_file_users(filename, message, exclude_conn=None):
    with lock:
        for conn, info in clients.items():
            if conn != exclude_conn and info.get("current_file") == filename:
                try:
                    conn.sendall((message + "\n").encode('utf-8'))
                except:
                    pass

def insert_text(text, index, content):
    try:
        line, char = map(int, index.split('.'))
        lines = text.split('\n')
        if line - 1 < len(lines):
            line_text = lines[line - 1]
            new_line_text = line_text[:char] + content + line_text[char:]
            lines[line - 1] = new_line_text
            return '\n'.join(lines)
        else:
            return text + content
    except:
        return text + content

def delete_text(text, index):
    try:
        line, char = map(int, index.split('.'))
        lines = text.split('\n')
        if line - 1 < len(lines):
            line_text = lines[line - 1]
            if char > 0:
                new_line_text = line_text[:char - 1] + line_text[char:]
                lines[line - 1] = new_line_text
                return '\n'.join(lines)
        return text
    except:
        return text

def handle_client(conn, addr):
    print(f"{addr} connected.")
    clients[conn] = {"username": None, "current_file": None}

    buffer = ""
    try:
        while True:
            data = conn.recv(4096)
            if not data:
                break
            buffer += data.decode('utf-8')
            while "\n" in buffer:
                msg_str, buffer = buffer.split("\n", 1)
                try:
                    msg_json = json.loads(msg_str)
                except:
                    continue

                action = msg_json.get('action')

                if action == 'set_username':
                    username = msg_json.get('username')
                    clients[conn]['username'] = username
                    files_list_msg = json.dumps({
                        'action': 'files_list',
                        'files': list(files.keys())
                    })
                    conn.sendall((files_list_msg + "\n").encode('utf-8'))

                elif action == 'create_file':
                    filename = msg_json.get('filename')
                    with lock:
                        if filename not in files:
                            files[filename] = ""
                            save_file(filename)
                    broadcast_msg = json.dumps({
                        'action': 'file_created',
                        'filename': filename
                    })
                    broadcast_to_file_users(None, broadcast_msg)

                elif action == 'open_file':
                    filename = msg_json.get('filename')
                    clients[conn]['current_file'] = filename
                    content = files.get(filename, "")
                    file_content_msg = json.dumps({
                        'action': 'file_content',
                        'filename': filename,
                        'content': content
                    })
                    conn.sendall((file_content_msg + "\n").encode('utf-8'))

                elif action == 'insert':
                    filename = msg_json.get('filename')
                    index = msg_json.get('index')
                    content = msg_json.get('content')
                    with lock:
                        if filename in files:
                            files[filename] = insert_text(files[filename], index, content)
                            save_file(filename)
                    # Değişikliği diğerlerine yolla
                    broadcast_to_file_users(filename, msg_str, exclude_conn=conn)

                elif action == 'delete':
                    filename = msg_json.get('filename')
                    index = msg_json.get('index')
                    with lock:
                        if filename in files:
                            files[filename] = delete_text(files[filename], index)
                            save_file(filename)
                    broadcast_to_file_users(filename, msg_str, exclude_conn=conn)

    except Exception as e:
        print(f"Error with {addr}: {e}")
    finally:
        print(f"{addr} disconnected.")
        with lock:
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
