const express = require('express');
const { createServer } = require('http');
const { Server } = require('socket.io');
const db = require('./db');

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, {
    cors: {
        origin: "*", // Cho phép tất cả origin
        methods: ["GET", "POST"]
    }
});

// Middleware để parse JSON
app.use(express.json());

// Hàm getMacAddress (tương tự Python)
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
        console.error(`Error retrieving MAC for ${ip}:`, e);
    }
    return "00:00:00:00:00:00";
}

// Hàm getIpFromMac (tương tự Python)
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
        console.error(`Error retrieving IP for ${mac}:`, e);
    }
    return null;
}

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'sender.html'));
});

app.get('/websocket_test', (req, res) => {
    res.sendFile(path.join(__dirname, 'websocket_test.html'));
});

// API verify_code
app.post('/verify_code', (req, res) => {
    const { code } = req.body;
    const device_ip = req.ip.replace('::ffff:', ''); // Xử lý IPv6

    if (!code) {
        return res.status(400).json({ success: false, message: "No code provided" });
    }

    db.get('SELECT id, mac_address FROM chromecasts WHERE code = ?', [code], (err, chromecast) => {
        if (err) {
            console.error('DB error:', err);
            return res.status(500).json({ success: false, message: "Server error" });
        }

        if (chromecast) {
            const { id: chromecast_id, mac_address: chromecast_mac } = chromecast;
            const chromecast_ip = getIpFromMac(chromecast_mac);
            console.log(`Handshake successful - Device IP: ${device_ip}, Code: ${code}, Chromecast IP: ${chromecast_ip}`);

            const mac_address = getMacAddress(device_ip);
            const pair_time = new Date().toISOString();

            db.run(
                'INSERT INTO pairs (chromecast_id, ip_address, mac_address, pair_time) VALUES (?, ?, ?, ?)',
                [chromecast_id, device_ip, mac_address, pair_time],
                function(err) {
                    if (err) {
                        console.error('Insert pair error:', err);
                        return res.status(500).json({ success: false, message: "Server error" });
                    }

                    db.get('SELECT COUNT(*) as count FROM pairs WHERE chromecast_id = ?', [chromecast_id], (err, row) => {
                        if (err) {
                            console.error('Count error:', err);
                            return res.status(500).json({ success: false, message: "Server error" });
                        }

                        const connections = row.count;
                        io.emit('connection_update', { chromecast_ip, connections });
                        res.json({ success: true, message: "Connected successfully" });
                    });
                }
            );
        } else {
            console.log(`Invalid code received from IP: ${device_ip}`);
            res.status(400).json({ success: false, message: "Invalid code" });
        }
    });
});

// API disconnect
app.post('/disconnect', (req, res) => {
    const device_ip = req.ip.replace('::ffff:', '');

    db.get('SELECT chromecast_id FROM pairs WHERE ip_address = ?', [device_ip], (err, pair) => {
        if (err) {
            console.error('DB error:', err);
            return res.status(500).json({ success: false, message: "Server error" });
        }

        if (pair) {
            const chromecast_id = pair.chromecast_id;

            db.run('DELETE FROM pairs WHERE ip_address = ?', [device_ip], (err) => {
                if (err) {
                    console.error('Delete pair error:', err);
                    return res.status(500).json({ success: false, message: "Server error" });
                }

                db.get('SELECT mac_address FROM chromecasts WHERE id = ?', [chromecast_id], (err, chromecast) => {
                    if (err) {
                        console.error('Get chromecast error:', err);
                        return res.status(500).json({ success: false, message: "Server error" });
                    }

                    const chromecast_ip = chromecast ? getIpFromMac(chromecast.mac_address) : null;
                    db.get('SELECT COUNT(*) as count FROM pairs WHERE chromecast_id = ?', [chromecast_id], (err, row) => {
                        if (err) {
                            console.error('Count error:', err);
                            return res.status(500).json({ success: false, message: "Server error" });
                        }

                        const connections = row.count;
                        console.log(`Device disconnected: ${device_ip}`);
                        io.emit('connection_update', { chromecast_ip, connections });
                        res.json({ success: true, message: "Disconnected successfully" });
                    });
                });
            });
        } else {
            res.status(404).json({ success: false, message: "Device not found" });
        }
    });
});

// Chạy server
const PORT = 8001;
httpServer.listen(PORT, '0.0.0.0', () => {
    console.log(`Server running at http://0.0.0.0:${PORT}`);
});