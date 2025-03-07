function sendCommand(command) {
    fetch('/send_command', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ command })
    })
    .then(response => response.json())
    .then(data => {
        if (!data.success) {
            alert('Failed to send command');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Server error');
    });
}

function openNetflix() {
    sendCommand('open_netflix');
}