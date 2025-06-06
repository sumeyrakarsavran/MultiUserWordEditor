# Çok Kullanıcılı Metin Editörü - Özellikleri Karşılayan Temel Yapı
# server.py

import socket
import threading
import os

HOST = '127.0.0.1'
PORT = 12345
BUFFER_SIZE = 1024
clients = {}
files = {}  # {filename: [client1, client2]}

if not os.path.exists("server_files"):
    os.makedirs("server_files")

def broadcast(filename, message, sender):
    for client in files.get(filename, []):
        if client != sender:
            try:
                client.sendall(message.encode('utf-8'))
            except:
                continue

def handle_client(client_socket, addr):
    try:
        username = client_socket.recv(BUFFER_SIZE).decode('utf-8')
        print(f"[+] Kullanici baglandi: {username} - {addr}")

        while True:
            data = client_socket.recv(BUFFER_SIZE).decode('utf-8')
            if not data:
                break

            command, *args = data.split("||")

            if command == "OPEN":
                filename = args[0]
                if filename not in files:
                    files[filename] = []
                files[filename].append(client_socket)

                filepath = f"server_files/{filename}.txt"
                if os.path.exists(filepath):
                    with open(filepath, "r", encoding='utf-8') as f:
                        content = f.read()
                else:
                    content = ""

                client_socket.sendall(f"LOAD||{filename}||{content}".encode('utf-8'))

            elif command == "EDIT":
                filename, content = args
                with open(f"server_files/{filename}.txt", "w", encoding='utf-8') as f:
                    f.write(content)
                broadcast(filename, f"UPDATE||{filename}||{content}", client_socket)

    except Exception as e:
        print(f"[-] Hata: {e}")
    finally:
        for clients_in_file in files.values():
            if client_socket in clients_in_file:
                clients_in_file.remove(client_socket)
        client_socket.close()
        print(f"[-] Baglanti kesildi: {addr}")


def start():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.bind((HOST, PORT))
    server.listen()
    print(f"[*] Sunucu baslatildi: {HOST}:{PORT}")

    try:
        while True:
            client, addr = server.accept()
            thread = threading.Thread(target=handle_client, args=(client, addr))
            thread.start()
    except KeyboardInterrupt:
        print("\n[!] Sunucu durduruluyor...")
    finally:
        server.close()

if __name__ == "__main__":
    start()
