function sendCommand(command) {
    const socket = io();
    socket.emit('remote_action', command);
}