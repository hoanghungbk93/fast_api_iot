const express = require('express');
const { createServer } = require('http');
const { Server } = require('socket.io');
const db = require('./db');
const path = require('path');
const winston = require('winston');

// Cấu hình logger với winston
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
        winston.format.printf(({ timestamp, level, message }) => {
            return `${timestamp} ${level.toUpperCase()}: ${message}`;
        })
    ),
    transports: [
        new winston.transports.Console(), // Xuất log ra console
        new winston.transports.File({ filename: 'server.log' }) // Lưu vào file
    ]
});

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

// Middleware để parse JSON
app.use(express.json());

// Middleware logging cho tất cả request
app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        logger.info(`${req.method} ${req.url} - IP: ${req.ip} - Status: ${res.statusCode} - ${duration}ms`);
    });
    next();
});

// Hàm getMacAddress
function getMacAddress(ip) {
    try {
        const { execSync } = require('child_process');
        const result = execSync(`arp -n ${ip}`).toString();
        for (const line of result.split('\n')) {
            if (line.includes(ip)) {
                return line.split(/\s+/)[2] || "00:00:00:00:00:00";
            }
        }
    } catch (e) {
        logger.error(`Error retrieving MAC for ${ip}: ${e.message}`);
    }
    return "00:00:00:00:00:00";
}

// Hàm getIpFromMac
function getIpFromMac(mac) {
    try {
        const { execSync } = require('child_process');
        const result = execSync('arp -n').toString();
        for (const line of result.split('\n')) {
            if (line.toLowerCase().includes(mac.toLowerCase())) {
                return line.split(/\s+/)[0];
            }
        }
    } catch (e) {
        logger.error(`Error retrieving IP for ${mac}: ${e.message}`);
    }
    return null;
}

// Socket.IO events
io.on('connection', (socket) => {
    logger.info(`Socket.IO Client connected: ${socket.id}`);
    socket.on('disconnect', () => {
        logger.info(`Socket.IO Client disconnected: ${socket.id}`);
    });
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'sender.html'));
});

app.get('/websocket_test', (req, res) => {
    res.sendFile(path.join(__dirname, 'websocket_test.html'));
});

// API verify_code
app.post('/verify_code', (req, res) => {
    const { code } = req.body;
    const device_ip = req.ip.replace('::ffff:', '');

    if (!code) {
        logger.warn(`No code provided from IP: ${device_ip}`);
        return res.status(400).json({ success: false, message: "No code provided" });
    }

    db.get('SELECT id, mac_address FROM chromecasts WHERE code = ?', [code], (err, chromecast) => {
        if (err) {
            logger.error(`DB error on verify_code: ${err.message}`);
            return res.status(500).json({ success: false, message: "Server error" });
        }

        if (chromecast) {
            const { id: chromecast_id, mac_address: chromecast_mac } = chromecast;
            const chromecast_ip = getIpFromMac(chromecast_mac);
            logger.info(`Handshake successful - Device IP: ${device_ip}, Code: ${code}, Chromecast IP: ${chromecast_ip}`);

            const mac_address = getMacAddress(device_ip);
            const pair_time = new Date().toISOString();

            db.run(
                'INSERT INTO pairs (chromecast_id, ip_address, mac_address, pair_time) VALUES (?, ?, ?, ?)',
                [chromecast_id, device_ip, mac_address, pair_time],
                function(err) {
                    if (err) {
                        logger.error(`Insert pair error: ${err.message}`);
                        return res.status(500).json({ success: false, message: "Server error" });
                    }

                    db.get('SELECT COUNT(*) as count FROM pairs WHERE chromecast_id = ?', [chromecast_id], (err, row) => {
                        if (err) {
                            logger.error(`Count error: ${err.message}`);
                            return res.status(500).json({ success: false, message: "Server error" });
                        }

                        const connections = row.count;
                        io.emit('connection_update', { chromecast_ip, connections });
                        logger.info(`Emitted connection_update: chromecast_ip=${chromecast_ip}, connections=${connections}`);
                        res.json({ success: true, message: "Connected successfully" });
                    });
                }
            );
        } else {
            logger.warn(`Invalid code received from IP: ${device_ip}`);
            res.status(400).json({ success: false, message: "Invalid code" });
        }
    });
});

// API disconnect
app.post('/disconnect', (req, res) => {
    const device_ip = req.ip.replace('::ffff:', '');

    db.get('SELECT chromecast_id FROM pairs WHERE ip_address = ?', [device_ip], (err, pair) => {
        if (err) {
            logger.error(`DB error on disconnect: ${err.message}`);
            return res.status(500).json({ success: false, message: "Server error" });
        }

        if (pair) {
            const chromecast_id = pair.chromecast_id;

            db.run('DELETE FROM pairs WHERE ip_address = ?', [device_ip], (err) => {
                if (err) {
                    logger.error(`Delete pair error: ${err.message}`);
                    return res.status(500).json({ success: false, message: "Server error" });
                }

                db.get('SELECT mac_address FROM chromecasts WHERE id = ?', [chromecast_id], (err, chromecast) => {
                    if (err) {
                        logger.error(`Get chromecast error: ${err.message}`);
                        return res.status(500).json({ success: false, message: "Server error" });
                    }

                    const chromecast_ip = chromecast ? getIpFromMac(chromecast.mac_address) : null;
                    db.get('SELECT COUNT(*) as count FROM pairs WHERE chromecast_id = ?', [chromecast_id], (err, row) => {
                        if (err) {
                            logger.error(`Count error: ${err.message}`);
                            return res.status(500).json({ success: false, message: "Server error" });
                        }

                        const connections = row.count;
                        logger.info(`Device disconnected: ${device_ip}`);
                        io.emit('connection_update', { chromecast_ip, connections });
                        logger.info(`Emitted connection_update: chromecast_ip=${chromecast_ip}, connections=${connections}`);
                        res.json({ success: true, message: "Disconnected successfully" });
                    });
                });
            });
        } else {
            logger.warn(`Device not found for IP: ${device_ip}`);
            res.status(404).json({ success: false, message: "Device not found" });
        }
    });
});


Dựa trên yêu cầu của bạn, tôi sẽ thêm một API mới vào app.js để lấy thông tin thiết bị (device info) khi Chromecast gọi lên server. API này sẽ:

Lấy IP của Chromecast từ request.
Tìm MAC address tương ứng bằng cách dùng arp -n.
Truy vấn cơ sở dữ liệu để lấy code của Chromecast và số lượng điện thoại đang kết nối (connections).
Trả về dữ liệu gồm code và connections.
Dưới đây là code đã cập nhật với API mới:

File app.js (Đã thêm API /device_info)
javascript
Wrap
Copy
const express = require('express');
const { createServer } = require('http');
const { Server } = require('socket.io');
const db = require('./db');
const path = require('path');
const winston = require('winston');

// Cấu hình logger với winston
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
        winston.format.printf(({ timestamp, level, message }) => {
            return `${timestamp} ${level.toUpperCase()}: ${message}`;
        })
    ),
    transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'server.log' })
    ]
});

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
    cors: {
        origin: "*",
        methods: ["GET", "POST"]
    }
});

// Middleware để parse JSON
app.use(express.json());

// Middleware logging cho tất cả request
app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        logger.info(`${req.method} ${req.url} - IP: ${req.ip} - Status: ${res.statusCode} - ${duration}ms`);
    });
    next();
});

// Hàm getMacAddress
function getMacAddress(ip) {
    try {
        const { execSync } = require('child_process');
        const result = execSync(`arp -n ${ip}`).toString();
        for (const line of result.split('\n')) {
            if (line.includes(ip)) {
                return line.split(/\s+/)[2] || "00:00:00:00:00:00";
            }
        }
        logger.warn(`No MAC found for IP: ${ip}`);
    } catch (e) {
        logger.error(`Error retrieving MAC for ${ip}: ${e.message}`);
    }
    return "00:00:00:00:00:00";
}

// Hàm getIpFromMac
function getIpFromMac(mac) {
    try {
        const { execSync } = require('child_process');
        const result = execSync('arp -n').toString();
        for (const line of result.split('\n')) {
            if (line.toLowerCase().includes(mac.toLowerCase())) {
                return line.split(/\s+/)[0];
            }
        }
        logger.warn(`No IP found for MAC: ${mac}`);
    } catch (e) {
        logger.error(`Error retrieving IP for ${mac}: ${e.message}`);
    }
    return null;
}

// Socket.IO events
io.on('connection', (socket) => {
    logger.info(`Socket.IO Client connected: ${socket.id}`);
    socket.on('disconnect', () => {
        logger.info(`Socket.IO Client disconnected: ${socket.id}`);
    });
});

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'sender.html'));
});

app.get('/websocket_test', (req, res) => {
    res.sendFile(path.join(__dirname, 'websocket_test.html'));
});

// API verify_code
app.post('/verify_code', (req, res) => {
    const { code } = req.body;
    const device_ip = req.ip.replace('::ffff:', '');

    if (!code) {
        logger.warn(`No code provided from IP: ${device_ip}`);
        return res.status(400).json({ success: false, message: "No code provided" });
    }

    db.get('SELECT id, mac_address FROM chromecasts WHERE code = ?', [code], (err, chromecast) => {
        if (err) {
            logger.error(`DB error on verify_code: ${err.message}`);
            return res.status(500).json({ success: false, message: "Server error" });
        }

        if (chromecast) {
            const { id: chromecast_id, mac_address: chromecast_mac } = chromecast;
            const chromecast_ip = getIpFromMac(chromecast_mac);
            logger.info(`Handshake successful - Device IP: ${device_ip}, Code: ${code}, Chromecast IP: ${chromecast_ip}`);

            const mac_address = getMacAddress(device_ip);
            const pair_time = new Date().toISOString();

            db.run(
                'INSERT INTO pairs (chromecast_id, ip_address, mac_address, pair_time) VALUES (?, ?, ?, ?)',
                [chromecast_id, device_ip, mac_address, pair_time],
                function(err) {
                    if (err) {
                        logger.error(`Insert pair error: ${err.message}`);
                        return res.status(500).json({ success: false, message: "Server error" });
                    }

                    db.get('SELECT COUNT(*) as count FROM pairs WHERE chromecast_id = ?', [chromecast_id], (err, row) => {
                        if (err) {
                            logger.error(`Count error: ${err.message}`);
                            return res.status(500).json({ success: false, message: "Server error" });
                        }

                        const connections = row.count;
                        io.emit('connection_update', { chromecast_ip, connections });
                        logger.info(`Emitted connection_update: chromecast_ip=${chromecast_ip}, connections=${connections}`);
                        res.json({ success: true, message: "Connected successfully" });
                    });
                }
            );
        } else {
            logger.warn(`Invalid code received from IP: ${device_ip}`);
            res.status(400).json({ success: false, message: "Invalid code" });
        }
    });
});

// API disconnect
app.post('/disconnect', (req, res) => {
    const device_ip = req.ip.replace('::ffff:', '');

    db.get('SELECT chromecast_id FROM pairs WHERE ip_address = ?', [device_ip], (err, pair) => {
        if (err) {
            logger.error(`DB error on disconnect: ${err.message}`);
            return res.status(500).json({ success: false, message: "Server error" });
        }

        if (pair) {
            const chromecast_id = pair.chromecast_id;

            db.run('DELETE FROM pairs WHERE ip_address = ?', [device_ip], (err) => {
                if (err) {
                    logger.error(`Delete pair error: ${err.message}`);
                    return res.status(500).json({ success: false, message: "Server error" });
                }

                db.get('SELECT mac_address FROM chromecasts WHERE id = ?', [chromecast_id], (err, chromecast) => {
                    if (err) {
                        logger.error(`Get chromecast error: ${err.message}`);
                        return res.status(500).json({ success: false, message: "Server error" });
                    }

                    const chromecast_ip = chromecast ? getIpFromMac(chromecast.mac_address) : null;
                    db.get('SELECT COUNT(*) as count FROM pairs WHERE chromecast_id = ?', [chromecast_id], (err, row) => {
                        if (err) {
                            logger.error(`Count error: ${err.message}`);
                            return res.status(500).json({ success: false, message: "Server error" });
                        }

                        const connections = row.count;
                        logger.info(`Device disconnected: ${device_ip}`);
                        io.emit('connection_update', { chromecast_ip, connections });
                        logger.info(`Emitted connection_update: chromecast_ip=${chromecast_ip}, connections=${connections}`);
                        res.json({ success: true, message: "Disconnected successfully" });
                    });
                });
            });
        } else {
            logger.warn(`Device not found for IP: ${device_ip}`);
            res.status(404).json({ success: false, message: "Device not found" });
        }
    });
});

// API device_info (mới)
app.get('/device_info', (req, res) => {
    const chromecast_ip = req.ip.replace('::ffff:', '');

    logger.info(`Device info requested from IP: ${chromecast_ip}`);
    const chromecast_mac = getMacAddress(chromecast_ip);

    db.get('SELECT id, code FROM chromecasts WHERE mac_address = ?', [chromecast_mac], (err, chromecast) => {
        if (err) {
            logger.error(`DB error on device_info: ${err.message}`);
            return res.status(500).json({ success: false, message: "Server error" });
        }

        if (chromecast) {
            const { id: chromecast_id, code } = chromecast;

            db.get('SELECT COUNT(*) as count FROM pairs WHERE chromecast_id = ?', [chromecast_id], (err, row) => {
                if (err) {
                    logger.error(`Count error on device_info: ${err.message}`);
                    return res.status(500).json({ success: false, message: "Server error" });
                }

                const connections = row.count;
                logger.info(`Device info retrieved - Chromecast IP: ${chromecast_ip}, MAC: ${chromecast_mac}, Code: ${code}, Connections: ${connections}`);
                res.json({
                    success: true,
                    data: {
                        code: code,
                        connections: connections
                    }
                });
            });
        } else {
            logger.warn(`Chromecast not found for MAC: ${chromecast_mac} (IP: ${chromecast_ip})`);
            res.status(404).json({ success: false, message: "Chromecast not found" });
        }
    });
});

// Chạy server
const PORT = 8001;
httpServer.listen(PORT, '0.0.0.0', () => {
    logger.info(`Server running at http://0.0.0.0:${PORT}`);
});