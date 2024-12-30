[Previous content remains unchanged up to openSongManageModal function]

async function openSongManageModal(mediaId) {
    currentMediaId = mediaId;
    loadSongPlaylists(mediaId);
    loadSongTags(mediaId);
    
    const mediaItem = mediaItems.find(item => item.id === mediaId);
    if (!mediaItem || !mediaItem.file_path) return;

    const filename = mediaItem.file_path.split('/').pop();
    const mediaUrl = `/media/${encodeURIComponent(filename)}`;
    
    let audioPreviewSection = document.querySelector('.audio-preview-section');
    let videoPreviewSection = document.querySelector('.video-preview-section');
    
    if (!audioPreviewSection) {
        audioPreviewSection = document.createElement('div');
        audioPreviewSection.className = 'audio-preview-section mb-4';
        audioPreviewSection.innerHTML = `
            <audio id="audioPreview" controls class="w-100 mb-2"></audio>
            <div style="height: 100px; background: #000; position: relative;">
                <canvas id="visualizer" style="position: absolute; top: 0; left: 0; width: 100%; height: 100%;"></canvas>
            </div>
        `;
    }
    
    if (!videoPreviewSection) {
        videoPreviewSection = document.createElement('div');
        videoPreviewSection.className = 'video-preview-section mb-4';
        videoPreviewSection.innerHTML = `
            <video id="videoPreview" controls class="w-100"></video>
        `;
    }
    
    const modalBody = document.querySelector('#songManageModal .modal-body');
    const previewContainer = modalBody.firstElementChild;
    
    previewContainer.innerHTML = '';
    
    if (mediaItem.type === 'audio') {
        previewContainer.appendChild(audioPreviewSection);
        videoPreviewSection.remove();
        
        audioPreview = document.getElementById('audioPreview');
        audioPreview.src = mediaUrl;
        
        if (visualizer) {
            await visualizer.cleanup();
            visualizer = new AudioVisualizer();
        }
        
        audioPreview.addEventListener('canplay', async () => {
            try {
                await audioPreview.play();
                audioPreview.pause();
            } catch (error) {
                console.error('Error starting audio context:', error);
                return;
            }
            
            try {
                await visualizer.initialize(audioPreview);
                
                audioPreview.addEventListener('play', () => visualizer.draw());
                audioPreview.addEventListener('pause', () => visualizer.stop());
                audioPreview.addEventListener('ended', () => visualizer.stop());
                
                if (!audioPreview.paused) {
                    visualizer.draw();
                }
            } catch (error) {
                console.error('Error initializing visualizer:', error);
            }
        }, { once: true });
        
        audioPreview.addEventListener('error', (e) => {
            console.error('Audio error:', e.target.error);
        });
    } else if (mediaItem.type === 'video') {
        previewContainer.appendChild(videoPreviewSection);
        audioPreviewSection.remove();
        
        const videoPreview = document.getElementById('videoPreview');
        videoPreview.src = mediaUrl;
    }
    
    const modal = new bootstrap.Modal(document.getElementById('songManageModal'));
    modal.show();
}

function loadSongPlaylists(mediaId) {
    const songPlaylists = document.getElementById('songPlaylists');
    songPlaylists.innerHTML = '<li class="list-group-item">Loading...</li>';

    fetch('/api/playlists')
        .then(response => response.json())
        .then(async playlists => {
            songPlaylists.innerHTML = '';
            const songPlaylistSelect = document.getElementById('songPlaylistSelect');
            songPlaylistSelect.innerHTML = '<option value="">Select Playlist</option>';

            for (const playlist of playlists) {
                const response = await fetch(`/api/playlist/${playlist.id}`);
                const playlistData = await response.json();
                const isInPlaylist = playlistData.items.some(item => item.media_id === mediaId);

                if (isInPlaylist) {
                    const li = document.createElement('li');
                    li.className = 'list-group-item d-flex justify-content-between align-items-center';
                    li.innerHTML = `
                        <span>${playlist.name}</span>
                        <button class="btn btn-sm btn-danger" onclick="removeSongFromPlaylist(${playlist.id})">
                            Remove
                        </button>
                    `;
                    songPlaylists.appendChild(li);
                } else {
                    const option = document.createElement('option');
                    option.value = playlist.id;
                    option.textContent = playlist.name;
                    songPlaylistSelect.appendChild(option);
                }
            }
        })
        .catch(error => console.error('Error:', error));
}

function loadSongTags(mediaId) {
    const songTags = document.getElementById('songTags');
    songTags.innerHTML = 'Loading...';

    fetch(`/api/media/${mediaId}/tags`)
        .then(response => response.json())
        .then(tags => {
            songTags.innerHTML = '';
            tags.forEach(tag => {
                const badge = document.createElement('span');
                badge.className = 'badge bg-primary me-1 mb-1';
                badge.innerHTML = `
                    ${tag.name}
                    <button type="button" class="btn-close btn-close-white" 
                            onclick="removeTagFromSong(${tag.id})" style="font-size: 0.5em;">
                    </button>
                `;
                songTags.appendChild(badge);
            });
        })
        .catch(error => console.error('Error:', error));
}

function addSongToPlaylist() {
    const playlistId = document.getElementById('songPlaylistSelect').value;
    if (!playlistId) return;

    fetch(`/api/playlist/${playlistId}/items`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ media_id: currentMediaId })
    })
        .then(() => {
            loadSongPlaylists(currentMediaId);
            loadPlaylists();
        })
        .catch(error => console.error('Error:', error));
}

function removeSongFromPlaylist(playlistId) {
    fetch(`/api/playlist/${playlistId}`)
        .then(response => response.json())
        .then(data => {
            const item = data.items.find(item => item.media_id === currentMediaId);
            if (item) {
                return fetch(`/api/playlist/${playlistId}/items/${item.id}`, {
                    method: 'DELETE'
                });
            }
        })
        .then(() => {
            loadSongPlaylists(currentMediaId);
            loadPlaylists();
        })
        .catch(error => console.error('Error:', error));
}

function addTagToSong() {
    const tagInput = document.getElementById('newTagInput');
    const tagName = tagInput.value.trim();
    if (!tagName) return;

    fetch(`/api/media/${currentMediaId}/tags`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ tags: [tagName] })
    })
        .then(() => {
            tagInput.value = '';
            loadSongTags(currentMediaId);
            loadTags();
        })
        .catch(error => console.error('Error:', error));
}

function removeTagFromSong(tagId) {
    fetch(`/api/media/${currentMediaId}/tags/${tagId}`, {
        method: 'DELETE'
    })
        .then(() => {
            loadSongTags(currentMediaId);
            loadTags();
        })
        .catch(error => console.error('Error:', error));
}
