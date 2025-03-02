document.addEventListener('DOMContentLoaded', function() {
    const chromecastList = document.getElementById('chromecasts');
    const addChromecastForm = document.getElementById('add-chromecast-form');
    const checkoutButton = document.getElementById('checkout-button');

    // Fetch and display chromecasts
    function fetchChromecasts() {
        fetch('/chromecasts/chromecasts')
            .then(response => response.json())
            .then(chromecasts => {
                chromecastList.innerHTML = '';
                chromecasts.forEach(chromecast => {
                    const li = document.createElement('li');
                    li.textContent = `${chromecast.code} (IP: ${chromecast.mac_address})`;
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

            fetch('/chromecasts/chromecasts', {
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

    // Checkout function
    function checkout() {
        fetch('/checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            }
        })
        .then(response => response.json())
        .then(data => {
            console.log('Checkout response:', data);
            // Optionally, update the UI or notify the user
        })
        .catch(error => {
            console.error('Error during checkout:', error);
        });
    }

    // Add event listener for checkout button
    if (checkoutButton) {
        checkoutButton.addEventListener('click', checkout);
    }

    // Initial fetch
    fetchChromecasts();
}); 