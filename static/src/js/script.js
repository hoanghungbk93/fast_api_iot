document.addEventListener('DOMContentLoaded', function() {
    const chromecastList = document.getElementById('chromecasts');
    const addChromecastForm = document.getElementById('add-chromecast-form');
    const checkoutButton = document.getElementById('checkout-button');

    let selectedChromecastId = null;

    // Fetch and display chromecasts
    function fetchChromecasts() {
        fetch('/chromecasts/chromecasts')
            .then(response => response.json())
            .then(chromecasts => {
                chromecastList.innerHTML = '';
                chromecasts.forEach(chromecast => {
                    const li = document.createElement('li');
                    li.textContent = `${chromecast.code} (MAC: ${chromecast.mac_address})`;

                    // Delete button
                    const deleteButton = document.createElement('button');
                    deleteButton.textContent = 'Delete';
                    deleteButton.onclick = () => deleteChromecast(chromecast.id);

                    // Select for checkout
                    const selectButton = document.createElement('button');
                    selectButton.textContent = 'Select';
                    selectButton.onclick = () => {
                        selectedChromecastId = chromecast.id;
                        alert(`Selected Chromecast: ${chromecast.code}`);
                    };

                    li.appendChild(selectButton);
                    li.appendChild(deleteButton);
                    chromecastList.appendChild(li);
                });
            });
    }

    // Checkout function
    function checkout() {
        if (!selectedChromecastId) {
            alert('Please select a Chromecast first!');
            return;
        }

        fetch('/chromecasts/checkout', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ chromecast_id: selectedChromecastId })
        })
        .then(response => response.json())
        .then(data => {
            console.log('Checkout response:', data);
            alert(`Checkout successful for Chromecast ID ${selectedChromecastId}`);
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
