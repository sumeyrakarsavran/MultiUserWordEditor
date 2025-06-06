import socket
import threading

HOST = 'localhost'
PORT = 12345

clients = []
server_socket = None

def handle_client(client_socket):
    clients.append(client_socket)
    while True:
        try:
            data = client_socket.recv(1024).decode('utf-8')
            if not data:
                break
            broadcast(data, sender=client_socket)
        except:
            break
    clients.remove(client_socket)
    client_socket.close()

def broadcast(message, sender=None):
    for client in clients:
        if client != sender:
            try:
                client.sendall(message.encode('utf-8'))
            except:
                pass

def start_server():
    global server_socket
    server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server_socket.bind((HOST, PORT))
    server_socket.listen()
    print(f"[SERVER] Listening on {HOST}:{PORT}")
    
    try:
        while True:
            client_socket, addr = server_socket.accept()
            print(f"[NEW CONNECTION] {addr}")
            threading.Thread(target=handle_client, args=(client_socket,), daemon=True).start()
    except KeyboardInterrupt:
        print("\n[SERVER] Shutting down...")
    finally:
        server_socket.close()
        for c in clients:
            try:
                c.close()
            except:
                pass
        print("[SERVER] Closed all connections and exited cleanly.")

if __name__ == "__main__":
    start_server()
