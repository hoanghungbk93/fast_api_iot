from scapy.all import *
import logging
from threading import Thread
import time
from fastapi import FastAPI, Response, HTTPException, Request, Depends
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey, Boolean, DateTime
from sqlalchemy.orm import declarative_base
from sqlalchemy.orm import sessionmaker, Session, relationship
import socket
import subprocess
import requests  # Thêm requests để gọi API
from datetime import datetime


# Hàm utils
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

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s:%(message)s")

ETH1_3 = "eth1.3"
ETH1_5 = "eth1.5"
PROXY_IP_ETH1_3 = "10.3.0.2"
PROXY_IP_ETH1_5 = "10.5.0.2"
MCAST_IP = "224.0.0.251"
SSDP_MCAST_IP = "239.255.255.250"
MDNS_MCAST_MAC = "01:00:5e:00:00:fb"
SSDP_MCAST_MAC = "01:00:5e:7f:ff:fa"

# Cấu hình SQLAlchemy
SQLALCHEMY_DATABASE_URL = "sqlite:////opt/fast_api_iot/test.db"
engine = create_engine(SQLALCHEMY_DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Chromecast(Base):
    __tablename__ = 'chromecasts'
    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    mac_address = Column(String, nullable=False)

    # Define the relationship to Pair
    pairs = relationship("Pair", back_populates="chromecast")

class Pair(Base):
    __tablename__ = 'pairs'
    id = Column(Integer, primary_key=True, index=True)
    chromecast_id = Column(Integer, ForeignKey('chromecasts.id'), nullable=False)
    ip_address = Column(String, nullable=False)
    mac_address = Column(String, nullable=False)
    pair_time = Column(DateTime, default=datetime.utcnow)
    active = Column(Boolean, default=True)

    chromecast = relationship("Chromecast", back_populates="pairs")

# Dependency để lấy session DB
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

app = FastAPI()

# Function kiểm tra thiết bị có được phép cast không
def is_device_allowed_to_cast(device_ip: str, db: Session):
    pair = db.query(Pair).filter(Pair.ip_address == device_ip).first()
    return pair is not None

# Function lấy danh sách IP thiết bị được phép cast dựa trên MAC của Chromecast
def get_list_device_allowed_to_cast(chromecast_mac: str, db: Session):
    chromecast = db.query(Chromecast).filter(Chromecast.mac_address == chromecast_mac).first()
    if chromecast:
        pairs = db.query(Pair).filter(Pair.chromecast_id == chromecast.id).all()
        return [pair.ip_address for pair in pairs]
    return []

# Endpoint sửa đổi để gọi sang Chromecast thực tế
@app.get("/ssdp/device-desc.xml")
async def device_description(request: Request, db: Session = Depends(get_db)):
    src_ip = request.client.host  # IP của thiết bị gửi yêu cầu (điện thoại)
    
    # Kiểm tra xem thiết bị có được phép không
    if not is_device_allowed_to_cast(src_ip, db):
        logging.warning(f"Thiết bị {src_ip} không được phép truy cập DIAL")
        raise HTTPException(status_code=403, detail="Forbidden")
    
    #logging.debug(f"Nhận request DIAL từ: {src_ip}, Headers: {dict(request.headers)}")
    
    # Tìm tất cả Chromecast mà thiết bị này đã pair
    paired_chromecasts = db.query(Pair).join(Chromecast).filter(Pair.ip_address == src_ip).all()
    
    if not paired_chromecasts:
        logging.warning(f"Không tìm thấy Chromecast nào pair với {src_ip}")
        raise HTTPException(status_code=404, detail="Không tìm thấy Chromecast được pair")
    
    # Giả định tạm thời: chọn Chromecast đầu tiên trong danh sách
    # Nếu cần chọn Chromecast cụ thể, có thể thêm logic dựa trên header hoặc tham số
    chromecast = paired_chromecasts[0].chromecast
    chromecast_ip = get_ip_from_mac(chromecast.mac_address)  # Lấy IP từ MAC của Chromecast
    
    if not chromecast_ip:
        logging.error(f"Không thể lấy IP từ MAC {chromecast.mac_address}")
        raise HTTPException(status_code=502, detail="Không thể xác định IP của Chromecast")
    
    # Gọi API của Chromecast thực tế
    chromecast_url = f"http://{chromecast_ip}:8008/ssdp/device-desc.xml"
    try:
        response = requests.get(chromecast_url, timeout=5)
        response.raise_for_status()
        xml_response = response.text
        logging.info(f"Thiết bị {src_ip} đã kết nối thành công tới Chromecast {chromecast_ip} qua proxy")
        return Response(content=xml_response, media_type="application/xml")
    except requests.RequestException as e:
        logging.error(f"Lỗi khi gọi tới Chromecast {chromecast_url}: {e}")
        raise HTTPException(status_code=502, detail="Không thể kết nối tới Chromecast")

def log_packet_details(pkt, prefix=""):
    if pkt.haslayer(DNS):
        dns = pkt[DNS]
        #logging.debug(f"{prefix}DNS QR: {'Response' if dns.qr else 'Query'}")
        #logging.debug(f"{prefix}DNS ID: {dns.id}")
        #logging.debug(f"{prefix}DNS QCOUNT: {dns.qdcount}")
        #logging.debug(f"{prefix}DNS ANCOUNT: {dns.ancount}")
        #logging.debug(f"{prefix}DNS NSCOUNT: {dns.nscount}")
        #logging.debug(f"{prefix}DNS ARCOUNT: {dns.arcount}")
        if dns.qdcount > 0 and dns.qd:
            logging.debug(f"{prefix}Questions:")
            for i, q in enumerate(dns.qd):
                try:
                    qname = q.qname.decode('utf-8', errors='ignore')
                    #logging.debug(f"{prefix}  Question {i+1}: {qname} (Type: {q.qtype}, Class: {q.qclass})")
                except Exception as e:
                    logging.debug(f"{prefix}  Question {i+1}: [Lỗi giải mã: {e}]")
        if dns.ancount > 0 and dns.an:
            #logging.debug(f"{prefix}Answers:")
            for i, ans in enumerate(dns.an):
                try:
                    rrname = ans.rrname.decode('utf-8', errors='ignore')
                    rdata = ans.rdata if isinstance(ans.rdata, str) else str(ans.rdata)
                    #logging.debug(f"{prefix}  Answer {i+1}: {rrname} (Type: {ans.type}, TTL: {ans.ttl}, Data: {rdata})")
                except Exception as e:
                    logging.debug(f"{prefix}  Answer {i+1}: [Lỗi giải mã: {e}]")
        if dns.arcount > 0 and dns.ar:
            #logging.debug(f"{prefix}Additional Records:")
            for i, ar in enumerate(dns.ar):
                try:
                    rrname = ar.rrname.decode('utf-8', errors='ignore')
                    if ar.type == 33:
                        rdata = f"Priority: {ar.priority}, Weight: {ar.weight}, Port: {ar.port}, Target: {ar.target.decode('utf-8', errors='ignore')}"
                    else:
                        rdata = ar.rdata if isinstance(ar.rdata, str) else str(ar.rdata)
                    #logging.debug(f"{prefix}  Additional {i+1}: {rrname} (Type: {ar.type}, Data: {rdata})")
                except Exception as e:
                    logging.debug(f"{prefix}  Additional {i+1}: [Lỗi giải mã: {e}]")

def handle_mdns_query(pkt, db: Session):
    if pkt.haslayer(IP) and pkt.haslayer(UDP) and pkt.haslayer(DNS):
        src_mac = pkt.src
        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst

        if not is_device_allowed_to_cast(src_ip, db):
            logging.debug(f"Query từ {src_ip} không được phép, bỏ qua")
            return

        #logging.info(f"Lưu thông tin iPhone: IP={src_ip}, MAC={src_mac}")
        #logging.debug(f"[+] Nhận Query từ {src_ip} (MAC: {src_mac}) tới {dst_ip}")
        log_packet_details(pkt, "    ")

        pkt[IP].src = PROXY_IP_ETH1_5
        pkt[Ether].src = "7c:c2:c6:3e:57:77"
        try:
            sendp(pkt, iface=ETH1_5, verbose=False)
            #logging.debug(f"Đã chuyển tiếp Query từ {src_ip} qua {ETH1_5} với Src IP {PROXY_IP_ETH1_5}")
        except Exception as e:
            logging.error(f"Lỗi khi chuyển tiếp Query: {e}")

def handle_mdns_response(pkt, db: Session):
    if pkt.haslayer(IP) and pkt.haslayer(UDP) and pkt.haslayer(DNS):
        src_ip = pkt[IP].src  # IP của Chromecast
        dst_ip = pkt[IP].dst

        chromecast = db.query(Chromecast).filter(Chromecast.mac_address == get_mac_address(src_ip)).first()
        if not chromecast:
            logging.debug(f"Response từ {src_ip} không phải Chromecast hợp lệ, bỏ qua")
            return

        #logging.debug(f"[+] Nhận Response từ Chromecast {src_ip} → {dst_ip}")
        log_packet_details(pkt, "    ")

        allowed_macs = db.query(Pair.mac_address).filter(
            Pair.chromecast_id == chromecast.id
        ).distinct().all()
        unique_macs = [mac[0] for mac in allowed_macs if mac[0]]

        if not unique_macs:
            logging.warning(f"Không tìm thấy điện thoại nào pair với Chromecast {chromecast.mac_address}")
            return

        pkt[IP].src = PROXY_IP_ETH1_3
        pkt[Ether].src = "7c:c2:c6:3e:57:77"
        for mac in unique_macs:
            pkt[Ether].dst = mac
            try:
                sendp(pkt, iface=ETH1_3, verbose=False)
                #logging.debug(f"Đã gửi Response tới {mac} qua {ETH1_3}")
            except Exception as e:
                logging.error(f"Lỗi khi chuyển tiếp Response tới {mac}: {e}")

def handle_ssdp_query(pkt, db: Session):
    if pkt.haslayer(IP) and pkt.haslayer(UDP) and pkt[UDP].dport == 1900:
        src_mac = pkt.src
        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst
        payload = pkt[Raw].load.decode('utf-8', errors='ignore') if pkt.haslayer(Raw) else ""

        if not is_device_allowed_to_cast(src_ip, db):
            logging.debug(f"SSDP Query từ {src_ip} không được phép, bỏ qua")
            return

        #logging.info(f"Lưu thông tin iPhone: IP={src_ip}, MAC={src_mac}")
        #logging.debug(f"[+] SSDP Query từ {src_ip} (MAC: {src_mac}) tới {dst_ip}: {payload}")

        if "M-SEARCH" in payload and "urn:dial-multiscreen-org:service:dial:1" in payload:
            allowed_macs = db.query(Pair.mac_address).distinct().all()
            unique_macs = [mac[0] for mac in allowed_macs if mac[0]]

            if not unique_macs:
                logging.warning("Không tìm thấy MAC nào trong danh sách thiết bị được phép pair.")
                return

            for mac in unique_macs:
                eth = Ether(dst=mac, src="7c:c2:c6:3e:57:77")
                ip = IP(src=PROXY_IP_ETH1_3, dst=src_ip, ttl=255)
                udp = UDP(sport=1900, dport=pkt[UDP].sport)
                ssdp_payload = (
                    "HTTP/1.1 200 OK\r\n"
                    f"HOST: {SSDP_MCAST_IP}:1900\r\n"
                    "CACHE-CONTROL: max-age=1800\r\n"
                    "LOCATION: http://10.3.0.2:8008/ssdp/device-desc.xml\r\n"
                    "ST: urn:dial-multiscreen-org:service:dial:1\r\n"
                    "USN: uuid:d8b5bd98-f15d-eb8a-2f3e-9acb21bed902::urn:dial-multiscreen-org:service:dial:1\r\n"
                    "SERVER: Linux/3.14.0 UPnP/1.0 Chromecast/1.0\r\n"
                    "BOOTID.UPNP.ORG: 1\r\n"
                    "CONFIGID.UPNP.ORG: 1\r\n"
                    "\r\n"
                ).encode('utf-8')
                response_pkt = eth / ip / udp / ssdp_payload
                try:
                    sendp(response_pkt, iface=ETH1_3, verbose=False)
                    logging.debug(f"Đã gửi SSDP Response unicast tới {mac}")
                except Exception as e:
                    logging.error(f"Lỗi khi gửi SSDP Response tới {mac}: {e}")

            pkt[IP].src = PROXY_IP_ETH1_5
            pkt[Ether].src = "7c:c2:c6:3e:57:77"
            try:
                sendp(pkt, iface=ETH1_5, verbose=False)
                #logging.debug(f"Đã chuyển tiếp SSDP Query từ {src_ip} qua {ETH1_5}")
            except Exception as e:
                logging.error(f"Lỗi khi chuyển tiếp SSDP Query: {e}")

def sniff_mdns_query():
    db = SessionLocal()
    try:
        sniff(filter="udp port 5353", prn=lambda pkt: handle_mdns_query(pkt, db), iface=ETH1_3, store=0, timeout=3600)
    finally:
        db.close()

def sniff_mdns_response():
    db = SessionLocal()
    try:
        sniff(filter="udp port 5353", prn=lambda pkt: handle_mdns_response(pkt, db), iface=ETH1_5, store=0, timeout=3600)
    finally:
        db.close()

def sniff_ssdp():
    db = SessionLocal()
    try:
        sniff(filter="udp port 1900", prn=lambda pkt: handle_ssdp_query(pkt, db), iface=ETH1_3, store=0, timeout=3600)
    finally:
        db.close()

if __name__ == "__main__":
    import uvicorn
    logging.info("[*] Đang chạy mDNS/SSDP Proxy relay thực tế từ 10.5.20.85 cho 10.3.0.64...")
    t1 = Thread(target=sniff_mdns_query)
    t2 = Thread(target=sniff_mdns_response)
    t5 = Thread(target=sniff_ssdp)
    t1.start()
    t2.start()
    t5.start()
    
    uvicorn.run(app, host="0.0.0.0", port=8008)