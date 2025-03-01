const sqlite3 = require('sqlite3').verbose();

const db = new sqlite3.Database('/opt/fast_api_iot/test.db', (err) => {
    if (err) {
        console.error('Error connecting to SQLite:', err.message);
    } else {
        console.log('Connected to SQLite database');
    }
});

module.exports = db;