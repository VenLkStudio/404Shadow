import socket
import struct
from typing import Optional, Tuple, List
from dataclasses import dataclass
import logging

@dataclass
class Packet:
    size: int
    data: bytes
    offset: int
    dynamic: bool

class PacketHandler:
    def __init__(self, buffer_size: int = 16384):
        self.buffer_size = buffer_size
        self.buffer = bytearray(buffer_size)
    
    def read_packet(self, sock: socket.socket) -> Optional[Packet]:
        try:
            data = sock.recv(self.buffer_size)
            if not data:
                return None
            return Packet(len(data), data, 0, False)
        except Exception as e:
            logging.error(f"Error reading packet: {e}")
            return None
    
    def write_packet(self, sock: socket.socket, packet: Packet) -> bool:
        try:
            sock.sendall(packet.data[packet.offset:packet.offset + packet.size])
            return True
        except Exception as e:
            logging.error(f"Error writing packet: {e}")
            return False
    
    def split_packet(self, packet: Packet, position: int) -> Tuple[Packet, Packet]:
        if position >= packet.size:
            return packet, Packet(0, b'', 0, False)
        
        first = Packet(position, packet.data[:position], 0, False)
        second = Packet(packet.size - position, packet.data[position:], 0, False)
        return first, second
    
    def create_fake_tls(self) -> Packet:
        # Basic TLS Client Hello packet
        tls_data = (
            b'\x16'  # TLS Handshake
            b'\x03\x01'  # TLS 1.0
            b'\x00\x2c'  # Length
            b'\x01'  # Client Hello
            b'\x00\x00\x28'  # Length
            b'\x03\x03'  # TLS 1.2
            b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00'  # Random
            b'\x00'  # Session ID length
            b'\x00\x04'  # Cipher suites length
            b'\x00\x2f'  # TLS_RSA_WITH_AES_128_CBC_SHA
            b'\x00\x35'  # TLS_RSA_WITH_AES_256_CBC_SHA
            b'\x01\x00'  # Compression methods length
            b'\x00'  # NULL compression
        )
        return Packet(len(tls_data), tls_data, 0, False)
    
    def create_fake_http(self) -> Packet:
        # Basic HTTP GET request
        http_data = (
            b'GET / HTTP/1.1\r\n'
            b'Host: example.com\r\n'
            b'User-Agent: Mozilla/5.0\r\n'
            b'Accept: */*\r\n'
            b'\r\n'
        )
        return Packet(len(http_data), http_data, 0, False)
    
    def create_fake_udp(self) -> Packet:
        # Basic UDP packet
        udp_data = b'\x00' * 8  # UDP header
        return Packet(len(udp_data), udp_data, 0, False)

# Global packet instances
fake_tls = PacketHandler().create_fake_tls()
fake_http = PacketHandler().create_fake_http()
fake_udp = PacketHandler().create_fake_udp() 