document.addEventListener('DOMContentLoaded', function() {
    const pairsTableBody = document.querySelector('#pairs-table tbody');

    function fetchPairs() {
        fetch('/pairs')
            .then(response => response.json())
            .then(pairs => {
                pairsTableBody.innerHTML = '';
                pairs.forEach(pair => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${pair[0]}</td>
                        <td>${pair[1]}</td>
                        <td>${pair[2]}</td>
                        <td>${pair[3]}</td>
                        <td>${pair[4]}</td>
                    `;
                    pairsTableBody.appendChild(row);
                });
            });
    }

    fetchPairs();
});
