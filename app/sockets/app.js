const express = require('express');
const { createServer } = require('http');
const { Server } = require('socket.io');
const db = require('./db');
const path = require('path');
const winston = require('winston');
const cors = require('cors'); // Thêm cors
const remoteActions = require('./virtual_remote');
const { exec } = require('child_process');
const { Client } = require('castv2-client'); // Thư viện điều khiển Chromecast


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

// Thêm middleware CORS cho tất cả route HTTP
app.use(cors({
    origin: "*", // Cho phép tất cả origin, bao gồm null
    methods: ["GET", "POST"]
}));

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

    socket.on('pair_success', (data) => {
        const { ip } = data;
        console.log(`Pairing successful with IP: ${ip}`);
        socket.emit('navigate', '/remote.html');

        socket.on('remote_action', (action) => {
            if (remoteActions[action]) {
                remoteActions[action](ip);
                console.log(`Action ${action} executed on IP: ${ip}`);
            } else {
                console.log(`Unknown action: ${action}`);
            }
        });

        socket.on('open_netflix', () => {
            remoteActions.open_netflix(ip);
            console.log(`Open Netflix executed on IP: ${ip}`);
        });
    });

    socket.on('disconnect', () => {
        console.log('user disconnected');
    });
});

app.use(express.static(path.join(__dirname, 'public')));

app.get('/', (req, res) => {
    res.sendFile(path.join(__dirname, 'public', 'sender.html'));
});

app.get('/websocket_test', (req, res) => {
    res.sendFile(path.join(__dirname, 'websocket_test.html'));
});

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

        console.log("Query Result:", chromecast);

        if (chromecast) {
            const { id: chromecast_id, mac_address: chromecast_mac } = chromecast;
            const chromecast_ip = getIpFromMac(chromecast_mac);
            logger.info(`Handshake successful - Device IP: ${device_ip}, Code: ${code}, Chromecast IP: ${chromecast_ip}`);

            const mac_address = getMacAddress(device_ip);
            const pair_time = new Date().toISOString().replace('Z', '');

            db.run(
                'INSERT INTO pairs (chromecast_id, ip_address, mac_address, pair_time, active) VALUES (?, ?, ?, ?, ?)',
                [chromecast_id, device_ip, mac_address, pair_time, true],
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

// API device_info
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

// API send_command

app.post('/send_command', (req, res) => {
    const { command } = req.body;
    const device_ip = req.ip.replace('::ffff:', '');

    logger.info(`Received command request: ${command} from ${device_ip}`);

    db.get('SELECT chromecast_id FROM pairs WHERE ip_address = ?', [device_ip], (err, pair) => {
        if (err) {
            logger.error(`DB error on send_command: ${err.message}`);
            return res.status(500).json({ success: false, message: "Server error" });
        }

        if (!pair) {
            logger.warn(`No paired device found for IP: ${device_ip}`);
            return res.status(404).json({ success: false, message: "Device not paired" });
        }

        const chromecast_id = pair.chromecast_id;

        db.get('SELECT mac_address FROM chromecasts WHERE id = ?', [chromecast_id], (err, chromecast) => {
            if (err) {
                logger.error(`DB error on chromecast lookup: ${err.message}`);
                return res.status(500).json({ success: false, message: "Server error" });
            }

            if (!chromecast) {
                logger.warn(`No Chromecast found for ID: ${chromecast_id}`);
                return res.status(404).json({ success: false, message: "Chromecast not found" });
            }

            const chromecast_ip = getIpFromMac(chromecast.mac_address);
            if (!chromecast_ip) {
                logger.error(`No IP found for Chromecast with MAC: ${chromecast.mac_address}`);
                return res.status(404).json({ success: false, message: "Chromecast IP not found" });
            }

            // Chỉ gọi res.json() **sau khi** lệnh ADB được thực thi xong
            sendCastCommand(chromecast_ip, command, (error) => {
                if (error) {
                    return res.status(500).json({ success: false, message: "Failed to execute command" });
                }
                res.json({ success: true, message: `Command '${command}' sent to Chromecast IP: ${chromecast_ip}` });
            });
        });
    });
});


function sendCastCommand(ip, command) {
    const client = new Client();

    client.connect(ip, () => {
        logger.info(`Connected to Chromecast at ${ip}`);

        client.getSessions((err, sessions) => {
            if (err) {
                logger.error(`Error getting sessions: ${err.message}`);
                client.close();
                return;
            }

            if (!sessions || sessions.length === 0) {
                logger.warn(`No active session found on Chromecast at ${ip}`);
                client.close();
                return;
            }

            const session = sessions[0]; // Chọn session đầu tiên
            client.join(session, DefaultMediaReceiver, (err, receiver) => {
                if (err) {
                    logger.error(`Error joining session: ${err.message}`);
                    client.close();
                    return;
                }

                // Gửi lệnh thông qua `InputChannel`
                const inputChannel = client.createChannel(
                    'sender-0',
                    'receiver-0',
                    'urn:x-cast:com.google.cast.input',
                    'JSON'
                );

                switch (command) {
                    case "up":
                        inputChannel.send({ type: "KEYPRESS", key: "KEY_UP" });
                        break;
                    case "down":
                        inputChannel.send({ type: "KEYPRESS", key: "KEY_DOWN" });
                        break;
                    case "left":
                        inputChannel.send({ type: "KEYPRESS", key: "KEY_LEFT" });
                        break;
                    case "right":
                        inputChannel.send({ type: "KEYPRESS", key: "KEY_RIGHT" });
                        break;
                    case "select":
                        inputChannel.send({ type: "KEYPRESS", key: "KEY_ENTER" });
                        break;
                    case "back":
                        inputChannel.send({ type: "KEYPRESS", key: "KEY_BACK" });
                        break;
                    case "home":
                        inputChannel.send({ type: "KEYPRESS", key: "KEY_HOME" });
                        break;
                    case "mute":
                        receiver.setVolume({ muted: true }, () => {
                            logger.info("Muted Chromecast");
                        });
                        break;
                    case "unmute":
                        receiver.setVolume({ muted: false }, () => {
                            logger.info("Unmuted Chromecast");
                        });
                        break;
                    case "open_netflix":
                        client.launchApp('Netflix', (err) => {
                            if (err) logger.error(`Error launching Netflix: ${err.message}`);
                        });
                        break;
                    default:
                        logger.warn(`Unknown command: ${command}`);
                }

                setTimeout(() => client.close(), 1000); // Đóng kết nối sau khi gửi lệnh
            });
        });
    });
}

function runAdbCommand(ip, command, callback) {
    const adbCommands = {
        "up": `adb -s ${ip}:5555 shell input keyevent 19`,
        "down": `adb -s ${ip}:5555 shell input keyevent 20`,
        "left": `adb -s ${ip}:5555 shell input keyevent 21`,
        "right": `adb -s ${ip}:5555 shell input keyevent 22`,
        "select": `adb -s ${ip}:5555 shell input keyevent 23`,
        "back": `adb -s ${ip}:5555 shell input keyevent 4`,
        "home": `adb -s ${ip}:5555 shell input keyevent 3`,
        "mute": `adb -s ${ip}:5555 shell service call audio 7 i32 3 i32 0`,
        "unmute": `adb -s ${ip}:5555 shell service call audio 7 i32 3 i32 1`,
        "open_netflix": `adb -s ${ip}:5555 shell monkey -p com.netflix.ninja -c android.intent.category.LAUNCHER 1`
    };

    const adbCommand = adbCommands[command];
    if (!adbCommand) {
        return callback(new Error("Invalid command"));
    }

    exec(adbCommand, (error, stdout, stderr) => {
        if (error) {
            console.error(`Error executing ADB command: ${error.message}`);
            return callback(error);
        }
        console.log(`ADB command executed: ${stdout}`);
        callback(null);
    });
}

// Chạy server
const PORT = 8001;
httpServer.listen(PORT, '0.0.0.0', () => {
    logger.info(`Server running at http://0.0.0.0:${PORT}`);
});