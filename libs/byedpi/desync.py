import socket
import logging
from typing import Optional, List, Tuple
from dataclasses import dataclass
from .packets import Packet, PacketHandler

@dataclass
class DesyncPart:
    mode: int
    flag: int
    pos: int
    repeats: int
    skip: int

class DesyncHandler:
    def __init__(self, packet_handler: PacketHandler):
        self.packet_handler = packet_handler
    
    def apply_desync(self, sock: socket.socket, packet: Packet, parts: List[DesyncPart]) -> bool:
        try:
            for part in parts:
                if not self._apply_part(sock, packet, part):
                    return False
            return True
        except Exception as e:
            logging.error(f"Error applying desync: {e}")
            return False
    
    def _apply_part(self, sock: socket.socket, packet: Packet, part: DesyncPart) -> bool:
        if part.mode == 0:  # NONE
            return self.packet_handler.write_packet(sock, packet)
        
        elif part.mode == 1:  # SPLIT
            first, second = self.packet_handler.split_packet(packet, part.pos)
            if not self.packet_handler.write_packet(sock, first):
                return False
            return self.packet_handler.write_packet(sock, second)
        
        elif part.mode == 2:  # DISORDER
            first, second = self.packet_handler.split_packet(packet, part.pos)
            if not self.packet_handler.write_packet(sock, second):
                return False
            return self.packet_handler.write_packet(sock, first)
        
        elif part.mode == 3:  # OOB
            first, second = self.packet_handler.split_packet(packet, part.pos)
            if not self.packet_handler.write_packet(sock, first):
                return False
            # Send OOB data
            sock.send(b'\x00', socket.MSG_OOB)
            return self.packet_handler.write_packet(sock, second)
        
        elif part.mode == 4:  # DISOOB
            first, second = self.packet_handler.split_packet(packet, part.pos)
            if not self.packet_handler.write_packet(sock, second):
                return False
            # Send OOB data
            sock.send(b'\x00', socket.MSG_OOB)
            return self.packet_handler.write_packet(sock, first)
        
        elif part.mode == 5:  # FAKE
            first, second = self.packet_handler.split_packet(packet, part.pos)
            if not self.packet_handler.write_packet(sock, first):
                return False
            # Send fake packet
            fake = self.packet_handler.create_fake_tls()
            if not self.packet_handler.write_packet(sock, fake):
                return False
            return self.packet_handler.write_packet(sock, second)
        
        return False
    
    def parse_position(self, pos_str: str) -> Optional[DesyncPart]:
        try:
            # Format: offset[:repeats:skip][+flag1[flag2]]
            parts = pos_str.split('+')
            base = parts[0]
            flags = parts[1] if len(parts) > 1 else ''
            
            # Parse base part
            base_parts = base.split(':')
            pos = int(base_parts[0])
            repeats = int(base_parts[1]) if len(base_parts) > 1 else 1
            skip = int(base_parts[2]) if len(base_parts) > 2 else 0
            
            # Parse flags
            flag = 0
            if 's' in flags:
                flag |= 8  # OFFSET_SNI
            if 'h' in flags:
                flag |= 16  # OFFSET_HOST
            if 'n' in flags:
                flag |= 4  # OFFSET_RAND
            if 'e' in flags:
                flag |= 1  # OFFSET_END
            if 'm' in flags:
                flag |= 2  # OFFSET_MID
            
            return DesyncPart(0, flag, pos, repeats, skip)
        except Exception as e:
            logging.error(f"Error parsing position: {e}")
            return None 