import socket
import logging
import threading
from typing import Optional, Tuple
from .packets import PacketHandler
from .desync import DesyncHandler

class ProxyConnection:
    def __init__(self, client_sock: socket.socket, packet_handler: PacketHandler, desync_handler: DesyncHandler):
        self.client_sock = client_sock
        self.server_sock = None
        self.packet_handler = packet_handler
        self.desync_handler = desync_handler
        self.buffer_size = 16384
        self.running = False
    
    def handle(self):
        try:
            # Read SOCKS5 handshake
            handshake = self.client_sock.recv(3)
            if not handshake or handshake[0] != 0x05:
                logging.error("Invalid SOCKS5 handshake")
                return
            
            # Send authentication method
            self.client_sock.send(b'\x05\x00')
            
            # Read connection request
            request = self.client_sock.recv(4)
            if not request or request[0] != 0x05:
                logging.error("Invalid SOCKS5 request")
                return
            
            # Parse address
            addr_type = request[3]
            if addr_type == 0x01:  # IPv4
                addr = socket.inet_ntoa(self.client_sock.recv(4))
                port = int.from_bytes(self.client_sock.recv(2), 'big')
            elif addr_type == 0x03:  # Domain name
                domain_len = self.client_sock.recv(1)[0]
                addr = self.client_sock.recv(domain_len).decode()
                port = int.from_bytes(self.client_sock.recv(2), 'big')
            elif addr_type == 0x04:  # IPv6
                addr = socket.inet_ntop(socket.AF_INET6, self.client_sock.recv(16))
                port = int.from_bytes(self.client_sock.recv(2), 'big')
            else:
                logging.error(f"Unsupported address type: {addr_type}")
                return
            
            # Connect to target
            try:
                self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                self.server_sock.connect((addr, port))
                
                # Send success response
                response = b'\x05\x00\x00\x01' + socket.inet_aton('0.0.0.0') + (0).to_bytes(2, 'big')
                self.client_sock.send(response)
                
                # Start bidirectional forwarding
                self.running = True
                client_thread = threading.Thread(target=self._forward_client_to_server)
                server_thread = threading.Thread(target=self._forward_server_to_client)
                
                client_thread.start()
                server_thread.start()
                
                client_thread.join()
                server_thread.join()
                
            except Exception as e:
                logging.error(f"Error connecting to target: {e}")
                # Send failure response
                response = b'\x05\x01\x00\x01' + socket.inet_aton('0.0.0.0') + (0).to_bytes(2, 'big')
                self.client_sock.send(response)
                return
            
        except Exception as e:
            logging.error(f"Error in proxy connection: {e}")
        finally:
            self.cleanup()
    
    def _forward_client_to_server(self):
        try:
            while self.running:
                packet = self.packet_handler.read_packet(self.client_sock)
                if not packet:
                    break
                
                # Apply desync if needed
                if not self.desync_handler.apply_desync(self.server_sock, packet, []):
                    break
                
        except Exception as e:
            logging.error(f"Error forwarding client to server: {e}")
        finally:
            self.running = False
    
    def _forward_server_to_client(self):
        try:
            while self.running:
                packet = self.packet_handler.read_packet(self.server_sock)
                if not packet:
                    break
                
                if not self.packet_handler.write_packet(self.client_sock, packet):
                    break
                
        except Exception as e:
            logging.error(f"Error forwarding server to client: {e}")
        finally:
            self.running = False
    
    def cleanup(self):
        self.running = False
        try:
            if self.client_sock:
                self.client_sock.close()
            if self.server_sock:
                self.server_sock.close()
        except:
            pass

class ProxyServer:
    def __init__(self, host: str, port: int, packet_handler: PacketHandler, desync_handler: DesyncHandler):
        self.host = host
        self.port = port
        self.packet_handler = packet_handler
        self.desync_handler = desync_handler
        self.server_sock = None
        self.running = False
    
    def start(self):
        try:
            self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_sock.bind((self.host, self.port))
            self.server_sock.listen(5)
            
            self.running = True
            logging.info(f"Proxy server started on {self.host}:{self.port}")
            
            while self.running:
                try:
                    client_sock, addr = self.server_sock.accept()
                    logging.info(f"New connection from {addr}")
                    
                    connection = ProxyConnection(
                        client_sock,
                        self.packet_handler,
                        self.desync_handler
                    )
                    
                    # Handle connection in a new thread
                    thread = threading.Thread(target=connection.handle)
                    thread.daemon = True
                    thread.start()
                    
                except Exception as e:
                    logging.error(f"Error accepting connection: {e}")
                    
        except Exception as e:
            logging.error(f"Error starting proxy server: {e}")
        finally:
            self.cleanup()
    
    def stop(self):
        self.running = False
        self.cleanup()
    
    def cleanup(self):
        try:
            if self.server_sock:
                self.server_sock.close()
        except:
            pass 