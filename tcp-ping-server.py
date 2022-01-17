import socket
import sys

HOST = ''                 # Symbolic name meaning all available interfaces
PORT = sys.argv[1] if len(sys.argv) > 1 else 20000

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
    s.bind((HOST, PORT))
    s.listen(1)
    while True:
        conn, addr = s.accept()
        with conn:
            # print('Received connection from ', addr)
            while True:
                data = conn.recv(1024)
                st = data.decode('utf-8').strip()
                if st:
                    print(f' -> received from {addr}: {st}')
                if not data:
                    conn.sendall('Received'.encode('utf-8'))
                    break
