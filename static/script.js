const WS_URL = 'wss://ordmempool.space/ws'
const WS_RECONNECT_INTERVAL_MS = 5000;

function shortenString(str, length) {
    const firstN = str.substring(0, length);
    const lastN = str.substring(str.length - length);
    return `${firstN}...${lastN}`;
}

async function fetchInitialLatestImages() {
    const response = await fetch('/api/latest-images');
    const results = await response.json();
    const size = results.size;
    updateMempoolSize(size);
    const imageResults = results.result;
    updateInitialLatestImages(imageResults);
}

function updateInitialLatestImages(results) {
    const container = document.querySelector('#images-container');
    container.innerHTML = '';

    results.sort((a, b) => b.creation_time - a.creation_time);  // highest to lowest
    results.forEach(result => {
        const card = createCardFromResult(result);
        container.appendChild(card);
    });
}

function prependNewImages(results) {
    const container = document.querySelector('#images-container');
    results.sort((a, b) => a.creation_time - b.creation_time);  // lowest to highest
    results.forEach(result => {
        const card = createCardFromResult(result);
        container.prepend(card);
    });
}

function createCardFromResult(result) {
    const imagePath = result.image;
    const data = result.data;
    const card = document.createElement('div');
    card.classList.add('image-card');
    card.classList.add('not-mined-color');
    // connecting the card with tx_id
    card.setAttribute('tx_id', data.tx_id);

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
    return card;
}

function markTxAsDeleted(tx_id) {
    const container = document.querySelector('#images-container');
    for (const card of container.children) {
        const cardId = card.getAttribute('tx_id');
        if (cardId === tx_id) {
            const deletedInfo = document.createElement('div');
            deletedInfo.innerHTML = `
                <p style="background-color: red;"><strong>Already mined!</strong></p>            
            `;
            card.classList.remove('not-mined-color');
            card.classList.add('mined-color');
            card.appendChild(deletedInfo);
            break;
        }
    }
}

function updateMempoolSize(newSize) {
    const overall = document.querySelector('#overall');
    overall.innerHTML = `${newSize}`
}


function setupWebSocket() {
    const ws = new WebSocket(WS_URL);

    ws.addEventListener('open', (event) => {
        console.log('WebSocket connection opened:', event);
    });

    ws.addEventListener('message', (event) => {
        const results = JSON.parse(event.data);
        console.log('WebSocket message received:', results);
        if (results.type === 'new_tx') {
            prependNewImages(results.payload);
        } else if (results.type === 'tx_deleted') {
            markTxAsDeleted(results.payload);
        } else {
            console.error('Unknown WebSocket message type:', results.type);
        }
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

window.onload = () => {
    fetchInitialLatestImages();
    setupWebSocket();
};
