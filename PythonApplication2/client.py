import socket
import threading

def receive_messages(sock):
    while True:
        try:
            data = sock.recv(1024).decode()
            print(data)
        except:
            break

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect(("localhost", 12345))

username = input("Kullanıcı adınızı girin: ")

thread = threading.Thread(target=receive_messages, args=(client_socket,))
thread.daemon = True
thread.start()

while True:
    message = input()
    if message.lower() == "quit":
        break
    client_socket.sendall(f"{username}: {message}".encode())

client_socket.close()
