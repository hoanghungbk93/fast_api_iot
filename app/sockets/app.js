const express = require('express');
const { createServer } = require('http');
const { Server } = require('socket.io');
const db = require('./db');
const path = require('path');
const winston = require('winston');
const cors = require('cors');
const remoteActions = require('./virtual_remote');
const { exec } = require('child_process');
const adb = require('adbkit');
const LRU = require('lru-cache');

const client = adb.createClient();

// **LRU Cache for Chromecast IP & MAC**
const chromecastCache = new LRU({
    max: 100, // Store up to 100 devices
    ttl: 1000 * 60 * 60 // Cache for 1 hour
});

// **Initialize ADB for Chromecast**
async function initializeAdb(ip) {
    try {
        await client.connect(ip, 5555);
        console.log(`Connected to ${ip}:5555`);
    } catch (err) {
        console.error(`Failed to connect: ${err.message}`);
        throw err;
    }
}

// **Logger Setup**
const logger = winston.createLogger({
    level: 'info',
    format: winston.format.combine(
        winston.format.timestamp({ format: 'YYYY-MM-DD HH:mm:ss' }),
        winston.format.printf(({ timestamp, level, message }) => `${timestamp} ${level.toUpperCase()}: ${message}`)
    ),
    transports: [
        new winston.transports.Console(),
        new winston.transports.File({ filename: 'server.log' })
    ]
});

const app = express();
const httpServer = createServer(app);
const io = new Server(httpServer, { cors: { origin: "*", methods: ["GET", "POST"] } });
io.on('connection', (socket) => {
    const clientIp = socket.handshake.address;
    logger.info(`📌 [SOCKET.IO] Client Connected: ${socket.id} - IP: ${clientIp}`);

    // **When the client disconnects**
    socket.on('disconnect', (reason) => {
        logger.info(`🔌 [SOCKET.IO] Client Disconnected: ${socket.id} - IP: ${clientIp} - Reason: ${reason}`);
    });
});

app.use(express.json());
app.use(cors({ origin: "*", methods: ["GET", "POST"] }));

// **Middleware Logging**
app.use((req, res, next) => {
    const start = Date.now();
    res.on('finish', () => {
        const duration = Date.now() - start;
        logger.info(`${req.method} ${req.url} - IP: ${req.ip} - Status: ${res.statusCode} - ${duration}ms`);
    });
    next();
});

// **Cache Chromecast IP**
async function getChromecastIP(mac) {
    let ip = chromecastCache.get(mac);
    if (!ip) {
        console.log(`Cache miss for MAC: ${mac}, querying DB...`);
        ip = await new Promise((resolve, reject) => {
            db.get('SELECT ip_address FROM chromecasts WHERE mac_address = ?', [mac], (err, row) => {
                if (err) return reject(err);
                resolve(row ? row.ip_address : null);
            });
        });

        if (ip) {
            chromecastCache.set(mac, ip); // Cache it for future use
        }
    }
    return ip;
}

// **Pairing Request Handler**
app.post('/verify_code', (req, res) => {
    const { code } = req.body;
    const device_ip = req.ip.replace('::ffff:', '');

    if (!code) {
        logger.warn(`No code provided from IP: ${device_ip}`);
        return res.status(400).json({ success: false, message: "No code provided" });
    }

    db.get('SELECT id, mac_address FROM chromecasts WHERE code = ?', [code], async (err, chromecast) => {
        if (err) return res.status(500).json({ success: false, message: "Server error" });

        if (chromecast) {
            const { id: chromecast_id, mac_address: chromecast_mac } = chromecast;
            const chromecast_ip = await getChromecastIP(chromecast_mac);

            if (!chromecast_ip) return res.status(404).json({ success: false, message: "Chromecast not found" });

            db.run(
                'INSERT INTO pairs (chromecast_id, ip_address, mac_address, pair_time, active) VALUES (?, ?, ?, ?, ?)',
                [chromecast_id, device_ip, chromecast_mac, new Date().toISOString(), true],
                function(err) {
                    if (err) return res.status(500).json({ success: false, message: "Server error" });

                    io.emit('connection_update', { chromecast_ip });
                    res.json({ success: true, message: "Connected successfully" });
                }
            );
        } else {
            res.status(400).json({ success: false, message: "Invalid code" });
        }
    });
});

// **Send Command to Chromecast**
app.post('/send_command', async (req, res) => {
    const { command } = req.body;
    const device_ip = req.ip.replace('::ffff:', '');

    db.get('SELECT chromecast_id FROM pairs WHERE ip_address = ?', [device_ip], async (err, pair) => {
        if (err) return res.status(500).json({ success: false, message: "Server error" });

        if (!pair) return res.status(404).json({ success: false, message: "Device not paired" });

        db.get('SELECT mac_address FROM chromecasts WHERE id = ?', [pair.chromecast_id], async (err, chromecast) => {
            if (err) return res.status(500).json({ success: false, message: "Server error" });

            const chromecast_ip = await getChromecastIP(chromecast.mac_address);
            if (!chromecast_ip) return res.status(404).json({ success: false, message: "Chromecast IP not found" });

            runAdbCommand(chromecast_ip, command, (error) => {
                if (error) return res.status(500).json({ success: false, message: "Failed to execute command" });
                res.json({ success: true, message: `Command '${command}' sent to Chromecast` });
            });
        });
    });
});

// **Optimized ADB Command Execution**
async function runAdbCommand(ip, command, callback) {
    const adbCommands = {
        "up": "input keyevent 19",
        "down": "input keyevent 20",
        "left": "input keyevent 21",
        "right": "input keyevent 22",
        "select": "input keyevent 23",
        "back": "input keyevent 4",
        "home": "input keyevent 3",
        "mute": "service call audio 7 i32 3 i32 0",
        "unmute": "service call audio 7 i32 3 i32 1",
        "open_netflix": "monkey -p com.netflix.ninja -c android.intent.category.LAUNCHER 1"
    };

    const adbCommand = adbCommands[command];
    if (!adbCommand) return callback(new Error("Invalid command"));

    try {
        const serial = `${ip}:5555`;
        // const devices = await client.listDevices();
        // if (!devices.find(d => d.id === serial)) throw new Error(`Device ${serial} not found`);

        const stream = await client.shell(serial, adbCommand);
        let output = '';
        stream.on('data', (data) => { output += data.toString(); });
        stream.on('end', () => { callback(null); });
    } catch (error) {
        console.error(`Error executing ADB command: ${error.message}`);
        callback(error);
    }
}

app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'sender.html'));
});

app.get('/websocket_test', (req, res) => {
    res.sendFile(path.join(__dirname, 'websocket_test.html'));
});

// **Run Server**
const PORT = 8001;
httpServer.listen(PORT, '0.0.0.0', () => {
    logger.info(`Server running at http://0.0.0.0:${PORT}`);
});
