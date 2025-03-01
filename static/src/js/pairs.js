document.addEventListener('DOMContentLoaded', function() {
    const pairsTableBody = document.querySelector('#pairs-table tbody');

    function fetchPairs() {
        fetch('/pair/list')
            .then(response => response.json())
            .then(pairs => {
                pairsTableBody.innerHTML = '';
                pairs.forEach(pair => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${pair.id}</td>
                        <td>${pair.chromecast_id}</td>
                        <td>${pair.ip_address}</td>
                        <td>${pair.mac_address}</td>
                        <td>${pair.pair_time}</td>
                    `;
                    pairsTableBody.appendChild(row);
                });
            });
    }

    fetchPairs();
});
