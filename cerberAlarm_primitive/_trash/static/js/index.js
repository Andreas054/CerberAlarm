var lastUpdateTime = new Date();

document.addEventListener('DOMContentLoaded', function() {
    fetch('/api/getZones')
        .then(response => response.json())
        .then(data => {
            const tbody = document.querySelector('.table-zones-tbody');
            for (const [zone, details] of Object.entries(data)) {
                const row = document.createElement('tr');
                if (zone == 6) {
                    row.style.backgroundColor = 'rgba(0, 0, 255, 0.25)';
                }
                row.innerHTML = `
                    <td>${zone}</td>
                    <td>${details.friendlyName}</td>
                    <td id="status-${zone}">${details.status}</td>
                `;
                tbody.appendChild(row);
            }
        })
        .catch(error => console.error('Error fetching zones:', error));
    
    const linkGetPdf = document.querySelector('.link-getpdf');
    linkGetPdf.addEventListener('click', function(event) {
        event.preventDefault();
        window.open('/getPdf', '_blank');
    });

    function updateStatus() {
        fetch('/api/getZones')
            .then(response => response.json())
            .then(data => {
                // check first if {"error": "Arduino is not connected"}
                if (data.error) {
                    // create a new element and overlay it on the page to display OUT OF SYNC in red
                    const overlay = document.createElement('div');
                    overlay.style.position = 'absolute';
                    overlay.style.top = 0;
                    overlay.style.left = 0;
                    overlay.style.width = '100%';
                    overlay.style.height = '100%';
                    overlay.style.backgroundColor = 'rgba(255, 0, 0, 0.5)';
                    overlay.style.color = 'white';
                    overlay.style.fontSize = '2em';
                    overlay.style.textAlign = 'center';
                    overlay.style.paddingTop = '10%';
                    overlay.textContent = 'OUT OF SYNC';
                    document.body.appendChild(overlay);
                    return;
                }
                for (const [zone, details] of Object.entries(data)) {
                    const statusCell = document.getElementById(`status-${zone}`);
                    if (statusCell) {
                        // statusCell.textContent = details.status;
                        if (zone == 6) {
                            statusCell.textContent = details.status === 1 ? 'Disarmed' : 'Armed';
                            statusCell.style.color = details.status === 1 ? 'green' : 'red';
                        } else {
                            statusCell.textContent = details.status === 1 ? 'Open' : 'Closed';
                            statusCell.style.color = details.status === 1 ? 'red' : 'green';
                        }
                    }
                }
                const lastUpdateSpan = document.querySelector('.last-update');
                if (lastUpdateSpan) {
                    const now = new Date();
                    lastUpdateTime = now;
                    lastUpdateSpan.textContent = now.toLocaleTimeString();
                }
            })
            .catch(error => console.error('Error updating zones:', error));
    } setInterval(updateStatus, 2000);

    const buttons = document.querySelectorAll('.keypad-button');

    buttons.forEach(button => {
        button.addEventListener('click', function() {
            const key = this.getAttribute('data-key');
            sendKeyCommand(key, this);
        });
    });

    function sendKeyCommand(key, button) {
        fetch('/api/sendOneKey', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ key: key })
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                button.style.backgroundColor = 'green';
                setTimeout(() => {
                    button.style.backgroundColor = '';
                }, 500);
                console.log(data.message);

                // Update history
                const historySpan = document.querySelector('.history-keypad');
                if (historySpan) {
                    historySpan.textContent += ` ${key}`;
                }
            }
        })
        .catch(error => {
            console.error('Error:', error);
        });
    }



    function checkLastUpdateTime() {
        const currentTime = new Date();
        const timeDifference = (currentTime - lastUpdateTime) / 1000; // time difference in seconds
    
        if (timeDifference > 30) {
            alert('Out of sync');
        }
    } setInterval(checkLastUpdateTime, 30000);
    
});