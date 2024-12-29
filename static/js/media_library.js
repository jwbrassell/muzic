// Global state
let mediaItems = [];
let selectedItems = new Set();
let currentMediaId = null;
let allTags = [];
let visualizer = null;
let audioPreview = null;
let durationCache = new Map(); // Cache for audio durations
let currentFilters = {
    search: '',
    type: '',
    sortBy: 'title',
    tag: ''
};

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    loadMedia();
    loadPlaylists();
    loadTags();
    setupEventListeners();
    setupDragAndDrop();
    
    // Initialize audio preview and visualizer
    audioPreview = document.getElementById('audioPreview');
    visualizer = new AudioVisualizer();
    
    // Handle modal close
    document.getElementById('songManageModal').addEventListener('hidden.bs.modal', () => {
        audioPreview.pause();
        audioPreview.src = '';
        visualizer.stop();
        const videoPreview = document.getElementById('videoPreview');
        if (videoPreview) {
            videoPreview.pause();
            videoPreview.src = '';
        }
    });
});

function setupDragAndDrop() {
    const dropZone = document.getElementById('dragDropZone');
    const fileInput = document.getElementById('fileInput');

    // Handle click on drop zone
    dropZone.addEventListener('click', () => {
        fileInput.click();
    });

    // Handle file selection
    fileInput.addEventListener('change', (e) => {
        handleFiles(e.target.files);
    });

    // Prevent default drag behaviors
    ['dragenter', 'dragover', 'dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, preventDefaults, false);
        document.body.addEventListener(eventName, preventDefaults, false);
    });

    // Handle drag enter/leave visual feedback
    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.add('dragover');
        }, false);
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, () => {
            dropZone.classList.remove('dragover');
        }, false);
    });

    // Handle dropped files
    dropZone.addEventListener('drop', (e) => {
        const files = e.dataTransfer.files;
        handleFiles(files);
    }, false);
}

function preventDefaults(e) {
    e.preventDefault();
    e.stopPropagation();
}

function createUploadToast(title) {
    const toast = document.createElement('div');
    toast.className = 'upload-toast';
    toast.innerHTML = `
        <div class="header">
            <strong>${title}</strong>
            <button type="button" class="btn-close btn-sm" onclick="this.closest('.upload-toast').remove()"></button>
        </div>
        <div class="body">
            <div class="progress">
                <div class="progress-bar" role="progressbar" style="width: 0%" aria-valuenow="0" aria-valuemin="0" aria-valuemax="100"></div>
            </div>
            <div class="mt-2 small text-muted">Uploading...</div>
        </div>
    `;
    
    document.getElementById('toastContainer').appendChild(toast);
    
    // Auto-dismiss after 30 seconds
    setTimeout(() => {
        if (toast && toast.parentNode) {
            toast.remove();
        }
    }, 30000);
    
    return toast;
}

function updateToastProgress(toast, progress) {
    const progressBar = toast.querySelector('.progress-bar');
    const progressText = toast.querySelector('.text-muted');
    
    progressBar.style.width = `${progress}%`;
    progressBar.setAttribute('aria-valuenow', progress);
    
    if (progress === 100) {
        progressText.textContent = 'Upload complete!';
        progressBar.classList.add('bg-success');
    } else {
        progressText.textContent = `Uploading... ${progress}%`;
    }
}

async function handleFiles(files) {
    const validFiles = Array.from(files).filter(file => 
        (file.type.startsWith('audio/') || file.type.startsWith('video/')) && 
        !file.name.startsWith('._')
    );
    
    if (validFiles.length === 0) return;
    
    // Create a toast for this batch of files
    const toast = createUploadToast(`Uploading ${validFiles.length} file${validFiles.length > 1 ? 's' : ''}`);
    
    try {
        const formData = new FormData();
        validFiles.forEach(file => {
            formData.append('files', file);
            formData.append('paths', file.name);
        });
        
        const xhr = new XMLHttpRequest();
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
                const progress = Math.round((event.loaded / event.total) * 100);
                updateToastProgress(toast, progress);
            }
        });
        
        // Return a promise that resolves when the upload is complete
        await new Promise((resolve, reject) => {
            xhr.open('POST', '/api/upload');
            
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    const response = JSON.parse(xhr.responseText);
                    if (response.errors && response.errors.length > 0) {
                        console.error('Upload errors:', response.errors);
                        toast.querySelector('.text-muted').textContent = 'Some files failed to upload';
                        toast.querySelector('.progress-bar').classList.add('bg-warning');
                    }
                    resolve(response);
                } else {
                    reject(new Error('Upload failed'));
                }
            };
            
            xhr.onerror = () => {
                reject(new Error('Upload failed'));
            };
            
            xhr.send(formData);
        });
        
        // Refresh media list after successful upload
        scanMedia();
        
    } catch (error) {
        console.error('Error:', error);
        toast.querySelector('.text-muted').textContent = 'Upload failed';
        toast.querySelector('.progress-bar').classList.add('bg-danger');
    }
}

function loadTags() {
    fetch('/api/tags')
        .then(response => response.json())
        .then(tags => {
            allTags = tags;
            updateTagFilter();
        })
        .catch(error => console.error('Error:', error));
}

function updateTagFilter() {
    const tagFilter = document.getElementById('tagFilter');
    tagFilter.innerHTML = '<option value="">All Tags</option>';
    allTags.forEach(tag => {
        const option = document.createElement('option');
        option.value = tag.id;
        option.textContent = tag.name;
        tagFilter.appendChild(option);
    });
}

function setupEventListeners() {
    // Existing event listeners
    // Search input debounce
    let searchTimeout;
    document.getElementById('searchInput').addEventListener('input', (e) => {
        clearTimeout(searchTimeout);
        searchTimeout = setTimeout(() => {
            currentFilters.search = e.target.value.toLowerCase();
            applyFilters();
        }, 300);
    });

    // Type filter
    document.getElementById('typeFilter').addEventListener('change', (e) => {
        currentFilters.type = e.target.value;
        applyFilters();
    });

    // Sort selection
    document.getElementById('sortBy').addEventListener('change', (e) => {
        currentFilters.sortBy = e.target.value;
        applyFilters();
    });

    // Tag filter
    document.getElementById('tagFilter').addEventListener('change', (e) => {
        currentFilters.tag = e.target.value;
        applyFilters();
    });

    // Playlist selection change
    document.getElementById('playlistSelect').addEventListener('change', (e) => {
        const newPlaylistForm = document.getElementById('newPlaylistForm');
        newPlaylistForm.classList.toggle('d-none', e.target.value !== 'new');
    });
}

function loadMedia() {
    fetch('/api/media')
        .then(response => response.json())
        .then(media => {
            mediaItems = media;
            applyFilters();
        })
        .catch(error => console.error('Error:', error));
}

function applyFilters() {
    let filteredItems = [...mediaItems];

    // Apply search filter
    if (currentFilters.search) {
        filteredItems = filteredItems.filter(item => 
            item.title.toLowerCase().includes(currentFilters.search) ||
            item.artist.toLowerCase().includes(currentFilters.search)
        );
    }

    // Apply type filter
    if (currentFilters.type) {
        filteredItems = filteredItems.filter(item => item.type === currentFilters.type);
    }

    // Apply tag filter
    if (currentFilters.tag) {
        const tagId = parseInt(currentFilters.tag);
        filteredItems = filteredItems.filter(item => {
            return fetch(`/api/media/${item.id}/tags`)
                .then(response => response.json())
                .then(tags => tags.some(tag => tag.id === tagId))
                .catch(error => {
                    console.error('Error:', error);
                    return false;
                });
        });
    }

    // Apply sorting
    filteredItems.sort((a, b) => {
        const aValue = a[currentFilters.sortBy].toLowerCase();
        const bValue = b[currentFilters.sortBy].toLowerCase();
        return aValue.localeCompare(bValue);
    });

    renderMediaList(filteredItems);
}

function renderMediaList(items) {
    const mediaList = document.getElementById('mediaList');
    mediaList.innerHTML = '';

    items.forEach(item => {
        const li = document.createElement('li');
        li.className = 'list-group-item d-flex justify-content-between align-items-center';
        li.setAttribute('data-id', item.id);
        
        if (selectedItems.has(item.id)) {
            li.classList.add('selected-item');
        }

        const checkbox = document.createElement('input');
        checkbox.type = 'checkbox';
        checkbox.className = 'form-check-input me-2';
        checkbox.checked = selectedItems.has(item.id);
        checkbox.addEventListener('change', () => toggleItemSelection(item.id));

        const content = document.createElement('div');
        content.className = 'flex-grow-1 ms-2 d-flex justify-content-between align-items-center';
        
        const manageBtn = document.createElement('button');
        manageBtn.className = 'btn btn-sm btn-outline-primary';
        manageBtn.innerHTML = '<i class="fas fa-cog"></i> Manage';
        manageBtn.onclick = async (e) => {
            e.stopPropagation();
            await openSongManageModal(item.id);
        };

        const info = document.createElement('div');
        const durationId = `duration-${item.id}`;
        info.innerHTML = `
            <strong>${item.title}</strong>
            <span class="text-muted"> - ${item.artist}</span>
            <span class="badge bg-secondary ms-2">${item.type}</span>
            <span class="badge bg-info ms-2" id="${durationId}">Loading...</span>
            <div class="tags-container mt-1"></div>
        `;
        
        content.appendChild(info);
        content.appendChild(manageBtn);
        li.appendChild(checkbox);
        li.appendChild(content);
        mediaList.appendChild(li);

        // Load duration from cache or fetch it after element is in DOM
        if (item.type === 'audio' && item.file_path) {
            const durationElement = document.getElementById(durationId);
            if (durationCache.has(item.id)) {
                const duration = durationCache.get(item.id);
                const minutes = Math.floor(duration / 60);
                const seconds = duration % 60;
                durationElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
            } else {
                const audio = new Audio(`/media/${encodeURIComponent(item.file_path.split('/').pop())}`);
                audio.addEventListener('loadedmetadata', () => {
                    const duration = Math.round(audio.duration);
                    durationCache.set(item.id, duration);
                    const minutes = Math.floor(duration / 60);
                    const seconds = duration % 60;
                    durationElement.textContent = `${minutes}:${seconds.toString().padStart(2, '0')}`;
                    audio.remove(); // Clean up the audio element
                });
                audio.addEventListener('error', () => {
                    durationElement.textContent = 'N/A';
                    console.error('Error loading audio:', item.file_path);
                });
            }
        } else {
            const durationElement = document.getElementById(durationId);
            durationElement.textContent = 'N/A';
        }

        // Load and display tags
        fetch(`/api/media/${item.id}/tags`)
            .then(response => response.json())
            .then(tags => {
                const tagsContainer = info.querySelector('.tags-container');
                tags.forEach(tag => {
                    const badge = document.createElement('span');
                    badge.className = 'badge bg-info me-1';
                    badge.textContent = tag.name;
                    tagsContainer.appendChild(badge);
                });
            })
            .catch(error => console.error('Error:', error));
        
        
    });

    updateSelectedCount();
}

function toggleItemSelection(id) {
    if (selectedItems.has(id)) {
        selectedItems.delete(id);
    } else {
        selectedItems.add(id);
    }
    updateSelectedCount();
    applyFilters(); // Re-render to update visual state
}

function toggleSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAll');
    const filteredIds = mediaItems
        .filter(item => 
            (!currentFilters.search || 
                item.title.toLowerCase().includes(currentFilters.search) ||
                item.artist.toLowerCase().includes(currentFilters.search)) &&
            (!currentFilters.type || item.type === currentFilters.type)
        )
        .map(item => item.id);

    if (selectAllCheckbox.checked) {
        filteredIds.forEach(id => selectedItems.add(id));
    } else {
        filteredIds.forEach(id => selectedItems.delete(id));
    }

    updateSelectedCount();
    applyFilters();
}

function updateSelectedCount() {
    const count = selectedItems.size;
    document.getElementById('selectedCount').textContent = `${count} selected`;
    document.getElementById('addToPlaylistBtn').disabled = count === 0;
}

function loadPlaylists() {
    fetch('/api/playlists')
        .then(response => response.json())
        .then(playlists => {
            const playlistList = document.getElementById('playlistList');
            const playlistSelect = document.getElementById('playlistSelect');
            
            // Update playlist list
            playlistList.innerHTML = '';
            playlists.forEach(playlist => {
                const li = document.createElement('li');
                li.className = 'list-group-item';
                li.innerHTML = `
                    <div class="d-flex justify-content-between align-items-center">
                        <span>${playlist.name}</span>
                        <div class="dropdown">
                            <button class="btn btn-primary dropdown-toggle" type="button" data-bs-toggle="dropdown">
                                <i class="fas fa-play"></i> Launch
                            </button>
                            <ul class="dropdown-menu dropdown-menu-end">
                                <li><a class="dropdown-item" href="/media-display?playlist=${playlist.id}" onclick="event.preventDefault(); viewPlaylist(${playlist.id}, 'player')">
                                    <i class="fas fa-music"></i> Media Player
                                </a></li>
                                <li><a class="dropdown-item" href="/display?playlist=${playlist.id}" onclick="event.preventDefault(); viewPlaylist(${playlist.id}, 'display')">
                                    <i class="fas fa-desktop"></i> Display Window
                                </a></li>
                            </ul>
                        </div>
                        <button class="btn btn-danger btn-sm" onclick="deletePlaylist(${playlist.id})">
                            Delete
                        </button>
                    </div>
                `;
                playlistList.appendChild(li);
            });

            // Update playlist select in modal
            const currentOptions = Array.from(playlistSelect.options);
            currentOptions.slice(1).forEach(option => option.remove());
            
            playlists.forEach(playlist => {
                const option = document.createElement('option');
                option.value = playlist.id;
                option.textContent = playlist.name;
                playlistSelect.appendChild(option);
            });
        })
        .catch(error => console.error('Error:', error));
}

function purgeLibrary() {
    if (!confirm('Are you sure you want to purge all entries from the media library? This cannot be undone.')) {
        return;
    }

    fetch('/api/purge-library', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log('Library purged:', data);
            loadMedia();  // Refresh the media list
        })
        .catch(error => console.error('Error:', error));
}

function scanMedia() {
    fetch('/api/scan-media', { method: 'POST' })
        .then(response => response.json())
        .then(data => {
            console.log('Scan complete:', data);
            loadMedia();
        })
        .catch(error => console.error('Error:', error));
}

function updateFileCount(input) {
    const files = Array.from(input.files);
    const validFiles = files.filter(file => 
        (file.type.startsWith('audio/') || file.type.startsWith('video/')) && 
        !file.name.startsWith('._')
    );
    
    // Update file count
    const fileCount = document.getElementById('fileCount');
    fileCount.textContent = `${validFiles.length} valid media files found`;
    
    // Update directory display
    const fileDisplay = document.getElementById('fileDisplay');
    if (files.length > 0) {
        // Get the root directory name from the first file's path
        const rootDir = files[0].webkitRelativePath.split('/')[0];
        fileDisplay.textContent = rootDir;
    } else {
        fileDisplay.textContent = 'No directory selected';
    }

    // Enable/disable import button
    const importButton = document.getElementById('importButton');
    importButton.disabled = validFiles.length === 0;
}

function importDirectory() {
    const modal = new bootstrap.Modal(document.getElementById('directoryModal'));
    
    // Reset the form when modal is hidden
    document.getElementById('directoryModal').addEventListener('hidden.bs.modal', function () {
        document.getElementById('directoryInput').value = '';
        document.getElementById('fileDisplay').textContent = 'No directory selected';
        document.getElementById('fileCount').textContent = '';
        document.getElementById('importButton').disabled = true;
    });
    
    modal.show();
}

async function confirmImport() {
    const directoryInput = document.getElementById('directoryInput');
    const files = Array.from(directoryInput.files);
    const formData = new FormData();
    
    // Create a Set to track unique paths
    const seenPaths = new Set();
    const validFiles = [];
    
    files.forEach(file => {
        if (file.type.startsWith('audio/') || file.type.startsWith('video/')) {
            // Skip macOS metadata files
            if (file.name.startsWith('._')) {
                return;
            }
            
            // Get the relative path from the webkitRelativePath
            const relativePath = file.webkitRelativePath;
            
            // Skip if we've already seen this path
            if (seenPaths.has(relativePath)) {
                return;
            }
            
            // Add to seen paths
            seenPaths.add(relativePath);
            
            // Add both the file and its path to the form data
            formData.append('files', file);
            formData.append('paths', relativePath);
            validFiles.push(file);
        }
    });

    if (validFiles.length === 0) return;

    // Create a toast for this batch of files
    const toast = createUploadToast(`Importing ${validFiles.length} file${validFiles.length > 1 ? 's' : ''}`);
    
    try {
        const xhr = new XMLHttpRequest();
        
        // Track upload progress
        xhr.upload.addEventListener('progress', (event) => {
            if (event.lengthComputable) {
                const progress = Math.round((event.loaded / event.total) * 100);
                updateToastProgress(toast, progress);
            }
        });
        
        // Return a promise that resolves when the upload is complete
        await new Promise((resolve, reject) => {
            xhr.open('POST', '/api/upload');
            
            xhr.onload = () => {
                if (xhr.status >= 200 && xhr.status < 300) {
                    const response = JSON.parse(xhr.responseText);
                    if (response.errors && response.errors.length > 0) {
                        console.error('Upload errors:', response.errors);
                        toast.querySelector('.text-muted').textContent = 'Some files failed to upload';
                        toast.querySelector('.progress-bar').classList.add('bg-warning');
                    }
                    resolve(response);
                } else {
                    reject(new Error('Upload failed'));
                }
            };
            
            xhr.onerror = () => {
                reject(new Error('Upload failed'));
            };
            
            xhr.send(formData);
        });
        
        // Close the modal and refresh media list after successful upload
        bootstrap.Modal.getInstance(document.getElementById('directoryModal')).hide();
        scanMedia();
        
    } catch (error) {
        console.error('Error:', error);
        toast.querySelector('.text-muted').textContent = 'Upload failed';
        toast.querySelector('.progress-bar').classList.add('bg-danger');
    }
}

function addSelectedToPlaylist() {
    const modal = new bootstrap.Modal(document.getElementById('playlistModal'));
    modal.show();
}

function confirmAddToPlaylist() {
    const playlistSelect = document.getElementById('playlistSelect');
    const newPlaylistName = document.getElementById('newPlaylistName');
    let playlistPromise;

    if (playlistSelect.value === 'new') {
        if (!newPlaylistName.value.trim()) {
            alert('Please enter a playlist name');
            return;
        }
        playlistPromise = fetch('/api/playlists', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ name: newPlaylistName.value.trim() })
        })
            .then(response => response.json());
    } else {
        playlistPromise = Promise.resolve({ id: parseInt(playlistSelect.value) });
    }

    playlistPromise
        .then(playlist => {
            const addPromises = Array.from(selectedItems).map(mediaId =>
                fetch(`/api/playlist/${playlist.id}/items`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ media_id: mediaId })
                })
            );

            return Promise.all(addPromises).then(() => playlist.id);
        })
        .then(playlistId => {
            bootstrap.Modal.getInstance(document.getElementById('playlistModal')).hide();
            selectedItems.clear();
            updateSelectedCount();
            loadPlaylists();
            applyFilters();
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

function deletePlaylist(playlistId) {
    if (!confirm('Are you sure you want to delete this playlist?')) return;

    fetch(`/api/playlist/${playlistId}`, { method: 'DELETE' })
        .then(() => loadPlaylists())
        .catch(error => console.error('Error:', error));
}

function viewPlaylist(playlistId, mode = 'player') {
    if (mode === 'display') {
        // For display mode, open in new window
        window.open(`/display?playlist=${playlistId}`, '_blank', 'width=800,height=600');
    } else {
        // For media player mode, open media_display in new window
        window.open(`/media-display?playlist=${playlistId}`, '_blank', 'width=800,height=600');
    }
}

// Song Management Modal Functions
async function openSongManageModal(mediaId) {
    currentMediaId = mediaId;
    loadSongPlaylists(mediaId);
    loadSongTags(mediaId);
    
    // Get the media item
    const mediaItem = mediaItems.find(item => item.id === mediaId);
    if (!mediaItem || !mediaItem.file_path) return;

    const filename = mediaItem.file_path.split('/').pop();
    const mediaUrl = `/media/${encodeURIComponent(filename)}`;
    
    // Get or create preview elements based on media type
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
    
    // Get the modal body's first element (where preview should go)
    const modalBody = document.querySelector('#songManageModal .modal-body');
    const previewContainer = modalBody.firstElementChild;
    
    // Clear existing preview
    previewContainer.innerHTML = '';
    
    if (mediaItem.type === 'audio') {
        previewContainer.appendChild(audioPreviewSection);
        videoPreviewSection.remove();
        
        // Set up audio preview
        audioPreview = document.getElementById('audioPreview');
        audioPreview.src = mediaUrl;
        
        // Clean up existing visualizer if any
        if (visualizer) {
            await visualizer.cleanup();
            visualizer = new AudioVisualizer();
        }
        
        // Wait for audio to be ready and context to be available
        audioPreview.addEventListener('canplay', async () => {
            try {
                // Try to start audio context with a user gesture
                await audioPreview.play();
                audioPreview.pause();
            } catch (error) {
                console.error('Error starting audio context:', error);
                return;
            }
            
            try {
                await visualizer.initialize(audioPreview);
                
                // Set up visualization controls
                audioPreview.addEventListener('play', () => visualizer.draw());
                audioPreview.addEventListener('pause', () => visualizer.stop());
                audioPreview.addEventListener('ended', () => visualizer.stop());
                
                // Start visualization if audio is already playing
                if (!audioPreview.paused) {
                    visualizer.draw();
                }
            } catch (error) {
                console.error('Error initializing visualizer:', error);
            }
        }, { once: true });
        
        // Handle audio errors
        audioPreview.addEventListener('error', (e) => {
            console.error('Audio error:', e.target.error);
        });
    } else if (mediaItem.type === 'video') {
        previewContainer.appendChild(videoPreviewSection);
        audioPreviewSection.remove();
        
        // Set up video preview
        const videoPreview = document.getElementById('videoPreview');
        videoPreview.src = mediaUrl;
    }
    
    const modal = new bootstrap.Modal(document.getElementById('songManageModal'));
    modal.show();
}

function loadSongPlaylists(mediaId) {
    const songPlaylists = document.getElementById('songPlaylists');
    songPlaylists.innerHTML = '<li class="list-group-item">Loading...</li>';

    // Get all playlists and check which ones contain this song
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
    // First get the playlist items to find the correct item_id
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
