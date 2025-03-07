const socket = io();

function pairDevice() {
    const code = document.getElementById('code-input').value;
    fetch('/verify_code', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ code })
    })
    .then(response => response.json())
    .then(data => {
        if (data.success) {
            showStatus('Connected successfully!', 'success');
            showConnectedState();
        } else {
            showStatus(data.message, 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showStatus('Server error', 'error');
    });
}

function showStatus(message, status) {
    alert(`${status.toUpperCase()}: ${message}`);
}

function showConnectedState() {
    document.getElementById('pairing-screen').style.display = 'none';
    document.getElementById('remote-screen').style.display = 'block';
}

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
            showStatus('Command failed!', 'error');
        }
    })
    .catch(error => {
        console.error('Error:', error);
        showStatus('Network error', 'error');
    });
}
