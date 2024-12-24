function scanMedia() {
    fetch('/api/scan-media', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log('Scan complete:', data);
            loadMedia();
        })
        .catch(error => console.error('Error:', error));
}

function loadMedia() {
    fetch('/api/media')
        .then(response => response.json())
        .then(media => {
            const mediaList = document.getElementById('mediaList');
            mediaList.innerHTML = '';
            media.forEach(item => {
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.setAttribute('draggable', 'true');
                li.setAttribute('data-id', item.id);
                li.textContent = `${item.title} - ${item.artist}`;
                li.addEventListener('dragstart', (e) => {
                    e.dataTransfer.setData('text/plain', item.id);
                });
                mediaList.appendChild(li);
            });
        })
        .catch(error => console.error('Error:', error));
}

function loadPlaylists() {
    fetch('/api/playlists')
        .then(response => response.json())
        .then(playlists => {
            const playlistList = document.getElementById('playlistList');
            playlistList.innerHTML = '';
            playlists.forEach(playlist => {
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center mb-2">
                        ${playlist.name}
                        <div>
                            <button class="btn btn-primary btn-sm" onclick="playPlaylist(${playlist.id})">Play</button>
                            <button class="btn btn-success btn-sm" onclick="savePlaylist(${playlist.id})">Save</button>
                            <button class="btn btn-danger btn-sm" onclick="deletePlaylist(${playlist.id})">Delete</button>
                        </div>
                    </div>
                    <ul class="list-group playlist-items" data-playlist-id="${playlist.id}"></ul>
                `;
                playlistList.appendChild(li);

                // Make playlist items sortable
                const itemsList = li.querySelector('.playlist-items');
                new Sortable(itemsList, {
                    group: {
                        name: 'shared',
                        pull: true,
                        put: true
                    },
                    animation: 150,
                    onAdd: function(evt) {
                        const mediaId = evt.item.getAttribute('data-id');
                        addToPlaylist(playlist.id, mediaId);
                    },
                    onUpdate: function(evt) {
                        updatePlaylistOrder(playlist.id);
                    }
                });

                // Load playlist items
                fetch(`/api/playlist/${playlist.id}`)
                    .then(response => response.json())
                    .then(data => {
                        data.items.forEach(item => {
                            const itemLi = document.createElement('li');
                            itemLi.className = 'list-group-item';
                            itemLi.setAttribute('data-id', item.media_id);
                            itemLi.textContent = `${item.title} - ${item.artist}`;
                            itemsList.appendChild(itemLi);
                        });
                    })
                    .catch(error => console.error('Error:', error));
            });
        })
        .catch(error => console.error('Error:', error));
}

function addToPlaylist(playlistId, mediaId) {
    fetch(`/api/playlist/${playlistId}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_id: mediaId })
    })
        .then(response => response.json())
        .catch(error => console.error('Error:', error));
}

function updatePlaylistOrder(playlistId) {
    const playlist = document.querySelector(`[data-playlist-id="${playlistId}"]`);
    const items = Array.from(playlist.children).map((item, index) => ({
        id: item.getAttribute('data-id'),
        order_position: index
    }));

    fetch(`/api/playlist/${playlistId}/order`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items })
    })
        .catch(error => console.error('Error:', error));
}

function createPlaylist() {
    const name = prompt('Enter playlist name:');
    if (!name) return;

    fetch('/api/playlists', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name })
    })
        .then(response => response.json())
        .then(() => loadPlaylists())
        .catch(error => console.error('Error:', error));
}

async function playPlaylist(playlistId) {
    console.log('Starting playlist:', playlistId);
    
    // First, open the display window
    const display = openDisplayWindow();
    if (!display) {
        console.error('Could not open display window');
        return;
    }

    try {
        // Create a promise that resolves when the display window loads
        const windowLoadPromise = new Promise((resolve, reject) => {
            const checkWindow = setInterval(() => {
                if (display.document && display.document.readyState === 'complete') {
                    clearInterval(checkWindow);
                    clearTimeout(timeout);
                    resolve();
                }
            }, 100);

            // Timeout after 5 seconds
            const timeout = setTimeout(() => {
                clearInterval(checkWindow);
                reject(new Error('Display window load timeout'));
            }, 5000);
        });

        // Wait for window to load
        await windowLoadPromise;

        // Start the playlist
        const response = await fetch('/api/play', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ playlist_id: playlistId })
        });

        if (!response.ok) {
            throw new Error(`HTTP error! status: ${response.status}`);
        }

        const data = await response.json();
        if (data.error) {
            throw new Error(data.error);
        }

        console.log('Playlist started successfully:', data);

        // Send play command to display window
        display.postMessage('play', '*');

    } catch (error) {
        console.error('Error starting playlist:', error);
        // If there was an error, close the display window and try again
        if (display && !display.closed) {
            display.close();
        }
        setTimeout(() => playPlaylist(playlistId), 1000);
    }
}

function savePlaylist(playlistId) {
    const playlist = document.querySelector(`[data-playlist-id="${playlistId}"]`);
    const items = Array.from(playlist.children).map((item, index) => ({
        id: item.getAttribute('data-id'),
        order_position: index
    }));

    fetch(`/api/playlist/${playlistId}/order`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ items })
    })
        .then(() => {
            console.log('Playlist saved successfully');
        })
        .catch(error => console.error('Error:', error));
}

function deletePlaylist(playlistId) {
    if (!confirm('Delete this playlist?')) return;

    fetch(`/api/playlist/${playlistId}`, { method: 'DELETE' })
        .then(() => loadPlaylists())
        .catch(error => console.error('Error:', error));
}

function previousTrack() {
    const display = openDisplayWindow();
    if (!display) {
        console.error('Display window not found');
        return;
    }
    console.log('Previous track - Not implemented yet');
}

function nextTrack() {
    const display = openDisplayWindow();
    if (!display) {
        console.error('Display window not found');
        return;
    }
    fetch('/api/next', { method: 'POST' })
        .then(() => updateNowPlaying())
        .catch(error => console.error('Error:', error));
}

function toggleRepeat() {
    fetch('/api/toggle-repeat', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            const icon = document.getElementById('repeatIcon');
            icon.style.color = data.repeat ? '#0d6efd' : 'inherit';
            // Save state after toggling repeat
            return fetch('/api/save-state', { method: 'POST' });
        })
        .catch(error => console.error('Error:', error));
}

function toggleShuffle() {
    fetch('/api/toggle-shuffle', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            const icon = document.getElementById('shuffleIcon');
            icon.style.color = data.shuffle ? '#0d6efd' : 'inherit';
            // Save state after toggling shuffle
            return fetch('/api/save-state', { method: 'POST' });
        })
        .catch(error => console.error('Error:', error));
}

function savePlaylistState() {
    fetch('/api/save-state', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log('Playlist state saved:', data);
            // Flash the save icon to indicate success
            const saveIcon = document.querySelector('.fa-save');
            saveIcon.style.color = '#0d6efd';
            setTimeout(() => {
                saveIcon.style.color = 'inherit';
            }, 500);
        })
        .catch(error => console.error('Error saving playlist state:', error));
}

const audioPlayer = document.getElementById('audioPlayer');

function updateNowPlaying() {
    fetch('/api/now-playing')
        .then(response => response.json())
        .then(data => {
            const element = document.getElementById('nowPlaying');
            if (data.error) {
                element.textContent = 'No media playing';
                const playPauseIcon = document.getElementById('playPauseIcon');
                if (playPauseIcon) {
                    playPauseIcon.classList.remove('fa-pause');
                    playPauseIcon.classList.add('fa-play');
                }
            } else {
                element.textContent = `${data.title} - ${data.artist}`;
                const playPauseIcon = document.getElementById('playPauseIcon');
                if (playPauseIcon) {
                    playPauseIcon.classList.remove('fa-play');
                    playPauseIcon.classList.add('fa-pause');
                }
            }
        })
        .catch(error => console.error('Error:', error));
}

// Get reference to display window
let displayWindow = null;

function openDisplayWindow() {
    if (!displayWindow || displayWindow.closed) {
        console.log('Opening new display window...');
        displayWindow = window.open('/display', 'displayWindow', 'width=800,height=600');
    }
    return displayWindow;
}

function togglePlay() {
    const display = openDisplayWindow();
    if (!display) {
        console.error('Display window not found');
        return;
    }

    // Get the audio player from display window to check its state
    console.log('Toggling play state...');
    display.postMessage('togglePlay', '*');
}

// Text update functions
function updateMarqueeText() {
    const display = openDisplayWindow();
    const preview = document.getElementById('displayPreview').contentWindow;
    const text = document.getElementById('marqueeInput').value;
    const message = {
        type: 'updateText',
        target: 'marquee',
        text: text
    };
    
    // Update both main display and preview
    if (display) {
        display.postMessage(message, '*');
    }
    preview.postMessage(message, '*');
}

function updateFooterText() {
    const display = openDisplayWindow();
    const preview = document.getElementById('displayPreview').contentWindow;
    const text = document.getElementById('footerInput').value;
    const message = {
        type: 'updateText',
        target: 'footer',
        text: text
    };
    
    // Update both main display and preview
    if (display) {
        display.postMessage(message, '*');
    }
    preview.postMessage(message, '*');
}

// Initialize preview
document.addEventListener('DOMContentLoaded', () => {
    const preview = document.getElementById('displayPreview');
    preview.addEventListener('load', () => {
        // Ensure preview is muted
        preview.contentWindow.postMessage('mute', '*');
    });
});

// Setup drag and drop for files
const dropZone = document.getElementById('dropZone');

dropZone.addEventListener('dragover', (e) => {
    e.preventDefault();
    dropZone.style.backgroundColor = '#f8f9fa';
});

dropZone.addEventListener('dragleave', () => {
    dropZone.style.backgroundColor = '';
});

dropZone.addEventListener('drop', (e) => {
    e.preventDefault();
    dropZone.style.backgroundColor = '';
    
    const files = Array.from(e.dataTransfer.files);
    const formData = new FormData();
    files.forEach(file => formData.append('files', file));
    
    fetch('/api/upload', {
        method: 'POST',
        body: formData
    })
        .then(response => response.json())
        .then(() => {
            scanMedia();
        })
        .catch(error => console.error('Error:', error));
});

// Make media list sortable
new Sortable(document.getElementById('mediaList'), {
    group: {
        name: 'shared',
        pull: 'clone',
        put: false
    },
    sort: false,
    animation: 150
});

// Initial load
loadMedia();
loadPlaylists();
updateNowPlaying();
