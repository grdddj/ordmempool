const WS_URL = `wss://${window.location.host}/ws`
const WS_RECONNECT_INTERVAL_MS = 5000;
const MAX_RESULTS = 100;
let RESULTS = [];

function shortenString(str, length) {
    const firstN = str.substring(0, length);
    const lastN = str.substring(str.length - length);
    return `${firstN}...${lastN}`;
}

async function fetchLatestImages() {
    const response = await fetch('/api/latest-images');
    const results = await response.json();
    updateGlobalResults(results);
    updateImages();
}

function updateGlobalResults(newResults) {
    RESULTS = RESULTS.concat(newResults);
    RESULTS.sort((a, b) => b.creation_time - a.creation_time);
    RESULTS = RESULTS.filter(
        (obj, index, self) =>
            index === self.findIndex((t) => t.creation_time === obj.creation_time && t.image === obj.image)
    );
    RESULTS = RESULTS.slice(0, MAX_RESULTS);
    updateImages();
}

function updateImages() {
    const container = document.querySelector('#images-container');
    container.innerHTML = '';

    RESULTS.forEach(result => {
        const imagePath = result.image;
        const data = result.data;
        const card = document.createElement('div');
        card.classList.add('image-card');

        const img = document.createElement('img');
        img.src = `/static/pictures/${imagePath}`;

        let short_tx_id = '';
        let mempool_space_link = '';
        let ordinals_com_link = '';
        if (data.tx_id) {
            short_tx_id = shortenString(data.tx_id, 4);
            mempool_space_link = `https://mempool.space/tx/${data.tx_id}`;
            ordinals_com_link = `https://ordinals.com/inscription/${data.tx_id}i0`;
        }

        let feeRate = ''
        if (data.fee_rate) {
            let feeRetaFixed2 = data.fee_rate.toFixed(2);
            feeRate = `${feeRetaFixed2} sat/vB`;
        }

        let publishedLocalTime = '';
        if (data.timestamp) {
            const timestampInMs = data.timestamp * 1000;
            const date = new Date(timestampInMs);
            publishedLocalTime = date.toLocaleTimeString([], { hour12: false });
        }

        const info = document.createElement('div');
        info.classList.add('image-info');
        info.innerHTML = `
            <p><strong>TX ID:</strong> <a href="${mempool_space_link}" target="_blank">${short_tx_id}</a></p>
            <p><strong>Time:</strong> ${publishedLocalTime}</p>
            <p><strong>Content Length:</strong> ${data.content_length}</p>
            <p><strong>Content type:</strong> ${data.content_type}</p>
            <p><strong>Fee rate:</strong> ${feeRate}</p>
            <p><a href="${ordinals_com_link}" target="_blank">Future ordinals.com link</a></p>
        `;

        card.appendChild(img);
        card.appendChild(info);
        container.appendChild(card);
    });
}


function setupWebSocket() {
    const ws = new WebSocket(WS_URL);

    ws.addEventListener('open', (event) => {
        console.log('WebSocket connection opened:', event);
    });

    ws.addEventListener('message', (event) => {
        const results = JSON.parse(event.data);
        updateGlobalResults(results);
        updateImages();
    });

    ws.addEventListener('error', (event) => {
        console.error('WebSocket error:', event);
    });

    ws.addEventListener('close', (event) => {
        console.log('WebSocket connection closed:', event);
        // Try to reconnect after a delay
        setTimeout(() => {
            console.log('Attempting to reconnect...');
            setupWebSocket();
        }, WS_RECONNECT_INTERVAL_MS);
    });
}

window.addEventListener('DOMContentLoaded', () => {
    fetchLatestImages();
    setupWebSocket();
});
