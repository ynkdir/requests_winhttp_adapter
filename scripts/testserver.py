import socketserver


class HttpEchoServer(socketserver.BaseRequestHandler):
    def handle(self):
        data = self.request.recv(1024)
        self.request.sendall(b"HTTP/1.1 200 OK\r\n")
        self.request.sendall(b"Content-Length: %d\r\n" % len(data))
        self.request.sendall(b"\r\n")
        self.request.sendall(data)


if __name__ == "__main__":
    with socketserver.TCPServer(("127.0.0.1", 8000), HttpEchoServer) as server:
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
