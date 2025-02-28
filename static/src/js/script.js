document.addEventListener('DOMContentLoaded', function() {
    const chromecastList = document.getElementById('chromecasts');
    const addChromecastForm = document.getElementById('add-chromecast-form');

    // Fetch and display chromecasts
    function fetchChromecasts() {
        fetch('/chromecasts')
            .then(response => response.json())
            .then(chromecasts => {
                chromecastList.innerHTML = '';
                chromecasts.forEach(chromecast => {
                    const li = document.createElement('li');
                    li.textContent = `${chromecast[1]} (IP: ${chromecast[2]})`;
                    const deleteButton = document.createElement('button');
                    deleteButton.textContent = 'Delete';
                    deleteButton.onclick = () => deleteChromecast(chromecast[0]);
                    li.appendChild(deleteButton);
                    chromecastList.appendChild(li);
                });
            });
    }

    // Add chromecast
    if (addChromecastForm) {
        addChromecastForm.addEventListener('submit', function(event) {
            event.preventDefault();
            const chromecastCode = document.getElementById('chromecast_code').value;
            const chromecastIp = document.getElementById('chromecast_ip').value;

            fetch('/chromecasts', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    code: chromecastCode,
                    mac_address: chromecastIp
                })
            })
            .then(response => response.json())
            .then(() => {
                fetchChromecasts();
                addChromecastForm.reset();
            });
        });
    }

    // Delete chromecast
    function deleteChromecast(chromecastId) {
        fetch(`/chromecasts/${chromecastId}`, {
            method: 'DELETE'
        })
        .then(response => response.json())
        .then(() => fetchChromecasts());
    }

    // Initial fetch
    fetchChromecasts();
}); 