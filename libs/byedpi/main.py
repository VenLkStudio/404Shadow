import socket
import struct
import sys
import os
import argparse
from enum import Enum
from dataclasses import dataclass
from typing import List, Optional, Union, Dict, Any
import ipaddress
import logging
import signal

from .packets import PacketHandler, fake_tls, fake_http, fake_udp
from .desync import DesyncHandler, DesyncPart
from .proxy import ProxyServer

# Constants
VERSION = "17"

class DesyncMode(Enum):
    NONE = 0
    SPLIT = 1
    DISORDER = 2
    OOB = 3
    DISOOB = 4
    FAKE = 5

class AutoLevel(Enum):
    NOBUFF = -1
    NOSAVE = 0

@dataclass
class DesyncParams:
    ttl: int = 8
    md5sig: bool = False
    fake_data: Any = None
    udp_fake_count: int = 0
    fake_offset: Optional[DesyncPart] = None
    fake_sni_count: int = 0
    fake_sni_list: List[str] = None
    fake_mod: int = 0
    drop_sack: bool = False
    oob_char: bytes = b'\x00'
    
    parts: List[DesyncPart] = None
    mod_http: int = 0
    tlsrec: List[DesyncPart] = None
    
    proto: int = 0
    detect: int = 0
    hosts: Any = None
    ipset: Any = None
    pf: List[int] = None
    rounds: List[int] = None
    
    custom_dst_addr: Optional[tuple] = None
    custom_dst: bool = False
    
    file_ptr: Optional[bytes] = None
    file_size: int = 0

    def __post_init__(self):
        if self.fake_sni_list is None:
            self.fake_sni_list = []
        if self.parts is None:
            self.parts = []
        if self.tlsrec is None:
            self.tlsrec = []
        if self.pf is None:
            self.pf = [0, 0]
        if self.rounds is None:
            self.rounds = [0, 0]

class Params:
    def __init__(self):
        self.dp_count: int = 0
        self.dp: List[DesyncParams] = []
        self.await_int: int = 10
        self.wait_send: bool = False
        self.def_ttl: int = 0
        self.custom_ttl: bool = False
        
        self.tfo: bool = False
        self.timeout: int = 0
        self.auto_level: AutoLevel = AutoLevel.NOBUFF
        self.cache_ttl: int = 100800
        self.ipv6: bool = True
        self.resolve: bool = True
        self.udp: bool = True
        self.transparent: bool = False
        self.http_connect: bool = False
        self.max_open: int = 512
        self.debug: int = 0
        self.bfsize: int = 16384
        
        self.baddr: tuple = ('::', 0)  # IPv6 default
        self.laddr: tuple = ('0.0.0.0', 0)  # IPv4 default
        
        self.protect_path: Optional[str] = None
        self.pid_file: Optional[str] = None
        self.pid_fd: Optional[int] = None

# Global parameters instance
params = Params()

def parse_args():
    parser = argparse.ArgumentParser(description='Python implementation of byedpi')
    parser.add_argument('-i', '--ip', default='0.0.0.0', help='Listening IP')
    parser.add_argument('-p', '--port', type=int, default=1080, help='Listening port')
    parser.add_argument('-c', '--max-conn', type=int, default=512, help='Connection count limit')
    parser.add_argument('-N', '--no-domain', action='store_true', help='Deny domain resolving')
    parser.add_argument('-U', '--no-udp', action='store_true', help='Deny UDP association')
    parser.add_argument('-I', '--conn-ip', help='Connection binded IP')
    parser.add_argument('-b', '--buf-size', type=int, default=16384, help='Buffer size')
    parser.add_argument('-x', '--debug', type=int, default=0, help='Print logs, 0, 1 or 2')
    parser.add_argument('-g', '--def-ttl', type=int, help='TTL for all outgoing connections')
    
    # Desync options
    parser.add_argument('-s', '--split', help='Split position format: offset[:repeats:skip][+flag1[flag2]]')
    parser.add_argument('-d', '--disorder', help='Split and send reverse order')
    parser.add_argument('-o', '--oob', help='Split and send as OOB data')
    parser.add_argument('-q', '--disoob', help='Split and send reverse order as OOB data')
    parser.add_argument('-f', '--fake', help='Split and send fake packet')
    parser.add_argument('-t', '--ttl', type=int, default=8, help='TTL of fake packets')
    parser.add_argument('-O', '--fake-offset', help='Fake data start offset')
    parser.add_argument('-l', '--fake-data', help='Set custom fake packet')
    parser.add_argument('-e', '--oob-data', help='Set custom OOB data')
    
    return parser.parse_args()

def setup_logging(debug_level: int):
    level = logging.DEBUG if debug_level > 0 else logging.INFO
    logging.basicConfig(
        level=level,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )

def setup_signal_handlers(proxy_server: ProxyServer):
    def signal_handler(signum, frame):
        logging.info("Received signal to stop")
        proxy_server.stop()
        sys.exit(0)
    
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

def main():
    args = parse_args()
    
    # Setup logging
    setup_logging(args.debug)
    
    # Update global params
    params.ipv6 = not args.no_domain
    params.udp = not args.no_udp
    params.max_open = args.max_conn
    params.bfsize = args.buf_size
    params.debug = args.debug
    
    if args.def_ttl:
        params.def_ttl = args.def_ttl
        params.custom_ttl = True
    
    # Create handlers
    packet_handler = PacketHandler(buffer_size=params.bfsize)
    desync_handler = DesyncHandler(packet_handler)
    
    # Create and configure desync params if needed
    if any([args.split, args.disorder, args.oob, args.disoob, args.fake]):
        dp = DesyncParams()
        
        if args.split:
            part = desync_handler.parse_position(args.split)
            if part:
                part.mode = DesyncMode.SPLIT.value
                dp.parts.append(part)
        
        if args.disorder:
            part = desync_handler.parse_position(args.disorder)
            if part:
                part.mode = DesyncMode.DISORDER.value
                dp.parts.append(part)
        
        if args.oob:
            part = desync_handler.parse_position(args.oob)
            if part:
                part.mode = DesyncMode.OOB.value
                dp.parts.append(part)
        
        if args.disoob:
            part = desync_handler.parse_position(args.disoob)
            if part:
                part.mode = DesyncMode.DISOOB.value
                dp.parts.append(part)
        
        if args.fake:
            part = desync_handler.parse_position(args.fake)
            if part:
                part.mode = DesyncMode.FAKE.value
                dp.parts.append(part)
                dp.ttl = args.ttl
                
                if args.fake_data:
                    dp.fake_data = Packet(len(args.fake_data), args.fake_data.encode(), 0, False)
                else:
                    dp.fake_data = fake_tls
        
        params.dp.append(dp)
        params.dp_count += 1
    
    # Create and start proxy server
    proxy_server = ProxyServer(args.ip, args.port, packet_handler, desync_handler)
    setup_signal_handlers(proxy_server)
    
    try:
        proxy_server.start()
    except KeyboardInterrupt:
        logging.info("Received keyboard interrupt")
    finally:
        proxy_server.stop()

if __name__ == "__main__":
    main() 