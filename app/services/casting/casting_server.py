from scapy.all import *
import logging
from threading import Thread
import time
from flask import Flask, Response, request
import sqlite3

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s %(levelname)s:%(message)s")

ETH1_3 = "eth1.3"
ETH1_5 = "eth1.5"
CHROMECAST_IP = "10.5.20.85"
PROXY_IP_ETH1_3 = "10.3.0.2"
PROXY_IP_ETH1_5 = "10.5.0.2"
MCAST_IP = "224.0.0.251"
SSDP_MCAST_IP = "239.255.255.250"
MDNS_MCAST_MAC = "01:00:5e:00:00:fb"
SSDP_MCAST_MAC = "01:00:5e:7f:ff:fa"
IPHONE_MAC = ["b2:27:79:2a:aa:09"]

app = Flask(__name__)

# Lưu thông tin iPhone
iphone_info = {"ip": None, "mac": None}

# Function to check if a device is allowed to cast based on the new database structure
def is_device_allowed_to_cast(device_ip):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.id FROM pairs p
        JOIN chromecasts c ON p.chromecast_id = c.id
        WHERE p.ip_address = ?
    ''', (device_ip,))
    result = cursor.fetchone()
    conn.close()
    return result is not None

def _get_list_device_allowed_to_cast(chromecast_mac):
    conn = sqlite3.connect('database.db')
    cursor = conn.cursor()
    cursor.execute('''
        SELECT p.ip_address FROM pairs p
        JOIN chromecasts c ON p.chromecast_id = c.id
        WHERE c.mac_address = ?
    ''', (chromecast_mac,))
    result = cursor.fetchall()
    conn.close()
    return result

@app.route('/ssdp/device-desc.xml', methods=['GET'])
def device_description():
    src_ip = request.remote_addr
    # Check if the device is allowed to cast
    if not is_device_allowed_to_cast(src_ip):
        logging.warning(f"Thiết bị {src_ip} không được phép truy cập DIAL")
        return Response("Forbidden", status=403)
    logging.debug(f"Nhận request DIAL từ: {src_ip}, Headers: {request.headers}")
    xml_response = (
        '<?xml version="1.0"?>\n'
        '<root xmlns="urn:schemas-upnp-org:device-1-0">\n'
        '    <specVersion><major>1</major><minor>0</minor></specVersion>\n'
        '    <device>\n'
        '        <deviceType>urn:dial-multiscreen-org:device:dial:1</deviceType>\n'
        '        <friendlyName>101</friendlyName>\n'
        '        <manufacturer>Google Inc.</manufacturer>\n'
        '        <modelName>Chromecast</modelName>\n'
        '        <UDN>uuid:d8b5bd98-f15d-eb8a-2f3e-9acb21bed902</UDN>\n'
        '    </device>\n'
        '</root>'
    )
    logging.info(f"Thiết bị {src_ip} đã kết nối thành công tới Chromecast '101'")
    return Response(xml_response, mimetype='application/xml')

def log_packet_details(pkt, prefix=""):
    if pkt.haslayer(DNS):
        dns = pkt[DNS]
        logging.debug(f"{prefix}DNS QR: {'Response' if dns.qr else 'Query'}")
        logging.debug(f"{prefix}DNS ID: {dns.id}")
        logging.debug(f"{prefix}DNS QCOUNT: {dns.qdcount}")
        logging.debug(f"{prefix}DNS ANCOUNT: {dns.ancount}")
        logging.debug(f"{prefix}DNS NSCOUNT: {dns.nscount}")
        logging.debug(f"{prefix}DNS ARCOUNT: {dns.arcount}")
        if dns.qdcount > 0 and dns.qd:
            logging.debug(f"{prefix}Questions:")
            for i, q in enumerate(dns.qd):
                try:
                    qname = q.qname.decode('utf-8', errors='ignore')
                    logging.debug(f"{prefix}  Question {i+1}: {qname} (Type: {q.qtype}, Class: {q.qclass})")
                except Exception as e:
                    logging.debug(f"{prefix}  Question {i+1}: [Lỗi giải mã: {e}]")
        if dns.ancount > 0 and dns.an:
            logging.debug(f"{prefix}Answers:")
            for i, ans in enumerate(dns.an):
                try:
                    rrname = ans.rrname.decode('utf-8', errors='ignore')
                    rdata = ans.rdata if isinstance(ans.rdata, str) else str(ans.rdata)
                    logging.debug(f"{prefix}  Answer {i+1}: {rrname} (Type: {ans.type}, TTL: {ans.ttl}, Data: {rdata})")
                except Exception as e:
                    logging.debug(f"{prefix}  Answer {i+1}: [Lỗi giải mã: {e}]")
        if dns.arcount > 0 and dns.ar:
            logging.debug(f"{prefix}Additional Records:")
            for i, ar in enumerate(dns.ar):
                try:
                    rrname = ar.rrname.decode('utf-8', errors='ignore')
                    if ar.type == 33:
                        rdata = f"Priority: {ar.priority}, Weight: {ar.weight}, Port: {ar.port}, Target: {ar.target.decode('utf-8', errors='ignore')}"
                    else:
                        rdata = ar.rdata if isinstance(ar.rdata, str) else str(ar.rdata)
                    logging.debug(f"{prefix}  Additional {i+1}: {rrname} (Type: {ar.type}, Data: {rdata})")
                except Exception as e:
                    logging.debug(f"{prefix}  Additional {i+1}: [Lỗi giải mã: {e}]")

def handle_mdns_query(pkt):
    if pkt.haslayer(IP) and pkt.haslayer(UDP) and pkt.haslayer(DNS):
        src_mac = pkt.src
        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst

        # Chỉ xử lý Query từ iPhone (10.3.0.64)
        if not is_device_allowed_to_cast(src_ip):
            logging.debug(f"Query từ {src_ip} không được phép, bỏ qua")
            return

        logging.info(f"Lưu thông tin iPhone: IP={src_ip}, MAC={src_mac}")

        logging.debug(f"[+] Nhận Query từ {src_ip} (MAC: {src_mac}) tới {dst_ip}")
        log_packet_details(pkt, "    ")

        # Chuyển tiếp Query qua eth1.5 với Src IP = 10.5.0.2
        pkt[IP].src = PROXY_IP_ETH1_5
        pkt[Ether].src = "7c:c2:c6:3e:57:77"  # MAC proxy
        try:
            sendp(pkt, iface=ETH1_5, verbose=False)
            logging.debug(f"Đã chuyển tiếp Query từ {src_ip} qua {ETH1_5} với Src IP {PROXY_IP_ETH1_5}")
        except Exception as e:
            logging.error(f"Lỗi khi chuyển tiếp Query: {e}")

def handle_mdns_response(pkt):
    if pkt.haslayer(IP) and pkt.haslayer(UDP) and pkt.haslayer(DNS):
        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst

        # Chỉ xử lý Response từ Chromecast thật
        if not is_device_allowed_to_cast(src_ip):
            logging.debug(f"Response từ {src_ip} không được phép, bỏ qua")
            return

        logging.debug(f"[+] Nhận Response từ Chromecast {src_ip} → {dst_ip}")
        log_packet_details(pkt, "    ")

        # Thay Src IP thành 10.3.0.2 và gửi về iPhone qua eth1.3
        pkt[IP].src = PROXY_IP_ETH1_3
        pkt[Ether].dst = IPHONE_MAC[0]  # Dùng MAC multicast
        pkt[Ether].src = "7c:c2:c6:3e:57:77"  # MAC proxy

        try:
            sendp(pkt, iface=ETH1_3, verbose=False)
            #logging.debug(f"Đã chuyển tiếp Response từ {CHROMECAST_IP} qua {ETH1_3} tới {iphone_info['ip']} với Src IP {PROXY_IP_ETH1_3}")
        except Exception as e:
            logging.error(f"Lỗi khi chuyển tiếp Response: {e}")

def handle_ssdp_query(pkt):
    if pkt.haslayer(IP) and pkt.haslayer(UDP) and pkt[UDP].dport == 1900:
        src_mac = pkt.src
        src_ip = pkt[IP].src
        dst_ip = pkt[IP].dst
        payload = pkt[Raw].load.decode('utf-8', errors='ignore') if pkt.haslayer(Raw) else ""

        # Chỉ xử lý từ iPhone
        if not is_device_allowed_to_cast(src_ip):
            logging.debug(f"SSDP Query từ {src_ip} không được phép, bỏ qua")
            return

        logging.info(f"Lưu thông tin iPhone: IP={src_ip}, MAC={src_mac}")

        logging.debug(f"[+] SSDP Query từ {src_ip} (MAC: {src_mac}) tới {dst_ip}: {payload}")

        if "M-SEARCH" in payload and "urn:dial-multiscreen-org:service:dial:1" in payload:
            # Tạo SSDP Response từ proxy
            eth = Ether(dst=src_mac, src="7c:c2:c6:3e:57:77")
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
                logging.debug(f"Đã gửi SSDP Response unicast tới {src_ip}")
            except Exception as e:
                logging.error(f"Lỗi khi gửi SSDP Response: {e}")

            # Chuyển tiếp M-SEARCH qua eth1.5
            pkt[IP].src = PROXY_IP_ETH1_5
            pkt[Ether].src = "7c:c2:c6:3e:57:77"
            try:
                sendp(pkt, iface=ETH1_5, verbose=False)
                logging.debug(f"Đã chuyển tiếp SSDP Query từ {src_ip} qua {ETH1_5}")
            except Exception as e:
                logging.error(f"Lỗi khi chuyển tiếp SSDP Query: {e}")

def run_flask():
    app.run(host="0.0.0.0", port=8008, threaded=True)

def sniff_mdns_query():
    sniff(filter="udp port 5353", prn=handle_mdns_query, iface=ETH1_3, store=0, timeout=3600)

def sniff_mdns_response():
    sniff(filter="udp port 5353 and src host 10.5.20.85", prn=handle_mdns_response, iface=ETH1_5, store=0, timeout=3600)

def sniff_ssdp():
    sniff(filter="udp port 1900", prn=handle_ssdp_query, iface=ETH1_3, store=0, timeout=3600)

if __name__ == "__main__":
    logging.info("[*] Đang chạy mDNS/SSDP Proxy relay thực tế từ 10.5.20.85 cho 10.3.0.64...")
    t1 = Thread(target=sniff_mdns_query)
    t2 = Thread(target=sniff_mdns_response)
    t4 = Thread(target=run_flask)
    t5 = Thread(target=sniff_ssdp)
    t1.start()
    t2.start()
    t4.start()
    t5.start()
    t1.join()
    t2.join()
    t4.join()
    t5.join()