import socket
import threading
import time

clients = []
running = True

def handle_client(client_socket, address):
    print(f"{address} bağlandı.")
    while True:
        try:
            data = client_socket.recv(1024).decode()
            if not data:
                break
            print(f"{address} >> {data}")
            for c in clients:
                if c != client_socket:
                    c.sendall(f"{address} >> {data}".encode())
        except:
            break
    print(f"{address} ayrıldı.")
    clients.remove(client_socket)
    client_socket.close()

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind(("localhost", 12345))
server_socket.listen(5)
server_socket.settimeout(1.0)  # 1 saniye içinde accept() yanıt vermezse timeout olacak

print("Sunucu başlatıldı. CTRL + C ile durdurabilirsiniz.")

try:
    while running:
        try:
            client_socket, addr = server_socket.accept()
            clients.append(client_socket)
            thread = threading.Thread(target=handle_client, args=(client_socket, addr))
            thread.start()
        except socket.timeout:
            continue  # timeout olduysa loop'u tekrar et, kapanma kontrolü yap
except KeyboardInterrupt:
    print("\nSunucu kapatılıyor...")
    running = False
    for client in clients:
        client.close()
    server_socket.close()
    print("Sunucu başarıyla kapatıldı.")
