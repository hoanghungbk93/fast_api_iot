from typing import List, TypeVar, Generic
from sqlalchemy.orm import Session
from fastapi import HTTPException
import socket
import subprocess
import logging

T = TypeVar('T')

def paginate(query, page: int = 1, page_size: int = 10):
    total = query.count()
    items = query.offset((page - 1) * page_size).limit(page_size).all()
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "items": items
    } 

def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def get_mac_address(ip):
    try:
        result = subprocess.run(['arp', '-n', ip], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if ip in line:
                return line.split()[2]
    except Exception as e:
        print(f"Error retrieving MAC address for {ip}: {e}")
    return "00:00:00:00:00:00"

def get_ip_from_mac(mac_address):
    try:
        result = subprocess.run(['arp', '-n'], capture_output=True, text=True)
        for line in result.stdout.splitlines():
            if mac_address.lower() in line.lower():
                return line.split()[0]
        return None
    except Exception as e:
        logging.error(f"Error running arp -n: {e}")
        return None
