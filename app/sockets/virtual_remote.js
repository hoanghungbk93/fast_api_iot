const adbCommand = (command) => {
    const { exec } = require('child_process');
    exec(command, (error, stdout, stderr) => {
        if (error) {
            console.error(`exec error: ${error}`);
            return;
        }
        console.log(`stdout: ${stdout}`);
        console.error(`stderr: ${stderr}`);
    });
};

const remoteActions = {
    up: (ip) => adbCommand(`adb -s ${ip}:5555 shell input keyevent 19`),
    down: (ip) => adbCommand(`adb -s ${ip}:5555 shell input keyevent 20`),
    left: (ip) => adbCommand(`adb -s ${ip}:5555 shell input keyevent 21`),
    right: (ip) => adbCommand(`adb -s ${ip}:5555 shell input keyevent 22`),
    back: (ip) => adbCommand(`adb -s ${ip}:5555 shell input keyevent 4`),
    home: (ip) => adbCommand(`adb -s ${ip}:5555 shell input keyevent 3`),
    select: (ip) => adbCommand(`adb -s ${ip}:5555 shell input keyevent 23`),
    mute: (ip) => adbCommand(`adb -s ${ip}:5555 shell service call audio 7 i32 3 i32 0`),
    unmute: (ip) => adbCommand(`adb -s ${ip}:5555 shell service call audio 7 i32 3 i32 1`),
};

module.exports = remoteActions;