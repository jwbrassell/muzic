import { AudioVisualizer } from '/static/js/visualizer.js';

// Initialize the media display after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('Initializing MediaDisplay...');
    new MediaDisplay();
});

export class MediaDisplay {
    constructor() {
        console.log('MediaDisplay constructor called');
        this.audioPlayer = document.getElementById('audioPlayer');
        this.videoPlayer = document.getElementById('videoPlayer');
        this.visualizerContainer = document.getElementById('visualizerContainer');
        this.videoContainer = document.getElementById('videoContainer');
        this.isRepeat = true;  // Default to repeat mode
        this.isShuffle = false;
        this.currentMediaType = null;
        this.visualizer = null;
        this.isTransitioning = false;
        this.playbackMonitor = null;

            // Initialize players
            this.audioPlayer.preload = 'auto';
            this.videoPlayer.preload = 'auto';
            this.audioPlayer.loop = false;  // Ensure single song repeat is off
            this.videoPlayer.loop = false;
            
            // Enable autoplay
            this.audioPlayer.autoplay = true;
            this.videoPlayer.autoplay = true;

        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Start playback button
        document.getElementById('startPlayback').addEventListener('click', async () => {
            try {
                if (this.currentMediaType === 'audio') {
                    if (!this.visualizer) {
                        this.visualizer = new AudioVisualizer();
                    }
                    await this.visualizer.initialize(this.audioPlayer);
                    this.visualizer.switchVisualizer(true);
                }
                
                const player = this.currentMediaType === 'video' ? this.videoPlayer : this.audioPlayer;
                
                if (this.currentMediaType === 'video') {
                    this.videoPlayer.style.display = 'block';
                    this.videoContainer.style.display = 'block';
                    this.visualizerContainer.style.display = 'none';
                } else {
                    this.videoPlayer.style.display = 'none';
                    this.videoContainer.style.display = 'none';
                    this.visualizerContainer.style.display = 'block';
                }
                
                if (player.paused) {
                    await this.playMedia();
                    this.startContinuousPlayback();
                }
            } catch (error) {
                console.error('Error starting playback on click:', error);
            }
            document.getElementById('startPlayback').classList.add('hidden');
        }, { once: true });

        // Progress bar
        document.getElementById('progressBar').addEventListener('click', (e) => {
            const player = this.currentMediaType === 'video' ? this.videoPlayer : this.audioPlayer;
            const progressBar = e.currentTarget;
            const clickPosition = (e.pageX - progressBar.offsetLeft) / progressBar.offsetWidth;
            player.currentTime = clickPosition * player.duration;
        });

        // Play/Pause button
        document.getElementById('playPauseIcon').addEventListener('click', () => this.togglePlay());

        // Fullscreen button
        const fullscreenIcon = document.getElementById('fullscreenIcon');
        fullscreenIcon.addEventListener('click', () => this.toggleFullScreen());

        // Fullscreen change event
        document.addEventListener('fullscreenchange', () => {
            if (document.fullscreenElement) {
                fullscreenIcon.classList.remove('fa-expand');
                fullscreenIcon.classList.add('fa-compress');
            } else {
                fullscreenIcon.classList.remove('fa-compress');
                fullscreenIcon.classList.add('fa-expand');
            }
        });

        // Media ended event
        [this.audioPlayer, this.videoPlayer].forEach(player => {
            player.addEventListener('ended', async () => {
                if (this.isTransitioning) {
                    console.log('Already transitioning, skipping duplicate ended event');
                    return;
                }
                
                console.log('Media ended, transitioning to next track...');
                this.isTransitioning = true;
                
                try {
                    await this.nextTrack();
                } catch (error) {
                    console.error('Error during track transition:', error);
                    setTimeout(() => this.nextTrack(), 1000);
                } finally {
                    setTimeout(() => {
                        this.isTransitioning = false;
                    }, 500);
                }
            });

            // Error handling
            player.addEventListener('error', (e) => {
                const error = player.error;
                let errorMessage = 'Unknown error';
                
                if (error) {
                    switch (error.code) {
                        case MediaError.MEDIA_ERR_ABORTED:
                            errorMessage = 'Playback aborted by user';
                            break;
                        case MediaError.MEDIA_ERR_NETWORK:
                            errorMessage = 'Network error while loading media';
                            break;
                        case MediaError.MEDIA_ERR_DECODE:
                            errorMessage = 'Media decoding error';
                            break;
                        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
                            errorMessage = 'Media format not supported';
                            break;
                    }
                    console.error('Media error:', errorMessage, error.message);
                    
                    if (error.code === MediaError.MEDIA_ERR_NETWORK) {
                        console.log('Attempting to recover from network error...');
                        setTimeout(async () => {
                            try {
                                await this.updateNowPlaying();
                            } catch (err) {
                                console.error('Recovery failed:', err);
                            }
                        }, 2000);
                    }
                } else {
                    console.error('Media error event without error details:', e);
                }
            });

            // Add canplay event listener
            player.addEventListener('canplay', () => {
                console.log(`${player === this.videoPlayer ? 'Video' : 'Audio'} can start playing`);
            });

            // Add loadeddata event listener
            player.addEventListener('loadeddata', () => {
                console.log(`${player === this.videoPlayer ? 'Video' : 'Audio'} data loaded`);
            });
        });

        // Progress update
        setInterval(() => this.updateProgress(), 100);

        // Window messages
        window.addEventListener('message', async (event) => {
            console.log('Received message:', event.data);
            if (event.data === 'play') {
                try {
                    console.log('Received play command');
                    await this.updateNowPlaying();
                    await this.playMedia();
                    this.startContinuousPlayback();
                } catch (error) {
                    console.error('Error starting playback:', error);
                    setTimeout(async () => {
                        await this.updateNowPlaying();
                        await this.playMedia();
                        this.startContinuousPlayback();
                    }, 1000);
                }
            } else if (event.data === 'pause') {
                this.pauseMedia();
            } else if (event.data === 'togglePlay') {
                const player = this.currentMediaType === 'video' ? this.videoPlayer : this.audioPlayer;
                if (player.paused) {
                    await this.playMedia();
                } else {
                    this.pauseMedia();
                }
            } else if (event.data === 'mute') {
                this.audioPlayer.muted = true;
                this.videoPlayer.muted = true;
            } else if (event.data.type === 'updateText') {
                if (event.data.target === 'marquee') {
                    document.getElementById('marqueeText').textContent = event.data.text;
                } else if (event.data.target === 'footer') {
                    document.getElementById('footer').textContent = event.data.text;
                }
            }
        });

        // Start initialization
        console.log('Starting initialization...');
        this.initialize();
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    updateProgress() {
        const player = this.currentMediaType === 'video' ? this.videoPlayer : this.audioPlayer;
        if (!player.duration) return;
        
        const currentTime = player.currentTime;
        const duration = player.duration;
        const progress = (currentTime / duration) * 100;
        
        document.getElementById('progressFill').style.width = `${progress}%`;
        document.getElementById('currentTime').textContent = this.formatTime(currentTime);
        document.getElementById('duration').textContent = this.formatTime(duration);
    }

    async updateNextTrack() {
        try {
            const response = await fetch('/api/next-track');
            const data = await response.json();
            if (!data.error) {
                const artist = data.artist.toLowerCase().includes('unknown artist') ? 'TapForNerd' : data.artist;
                const cleanTitle = data.title.replace(/\.(mp3|wav|m4a|mp4|ogg|webm|flac|aac)$/i, '');
                document.getElementById('nextUpSong').textContent = `${cleanTitle} - ${artist}`;
            } else {
                document.getElementById('nextUpSong').textContent = 'End of playlist';
            }
        } catch (error) {
            console.error('Error fetching next track:', error);
            document.getElementById('nextUpSong').textContent = 'Unknown';
        }
    }

    updatePlayPauseIcon() {
        const player = this.currentMediaType === 'video' ? this.videoPlayer : this.audioPlayer;
        const icon = document.getElementById('playPauseIcon');
        icon.classList.remove('fa-play', 'fa-pause');
        icon.classList.add(player.paused ? 'fa-play' : 'fa-pause');
    }

    async togglePlay() {
        const player = this.currentMediaType === 'video' ? this.videoPlayer : this.audioPlayer;
        if (player.paused) {
            await this.playMedia();
        } else {
            this.pauseMedia();
        }
    }

    async nextTrack() {
        try {
            // Stop both players and visualizer
            this.audioPlayer.pause();
            this.audioPlayer.currentTime = 0;
            this.videoPlayer.pause();
            this.videoPlayer.currentTime = 0;
            if (this.visualizer) {
                this.visualizer.stop();
            }

            const response = await fetch('/api/next', { method: 'POST' });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            if (data.error) {
                console.log('End of playlist reached or error:', data.error);
                if (this.isRepeat) {
                    console.log('Repeat is on, restarting playlist');
                    await this.updateNowPlaying();
                } else {
                    document.getElementById('nowPlaying').textContent = 'End of playlist';
                    this.pauseMedia();
                    this.updatePlayPauseIcon();
                }
                return;
            }

            await this.loadMedia(data);
            await this.playMedia();
            this.updateNextTrack();
            
        } catch (error) {
            console.error('Error during track transition:', error);
            setTimeout(() => this.nextTrack(), 1000);
        }
    }

    async loadMedia(data) {
        if (!data || !data.file_path) {
            console.error('Invalid media data:', data);
            throw new Error('Invalid media data: missing file path');
        }

        try {
            console.log('Loading media:', data);
            const artist = data.artist?.toLowerCase().includes('unknown artist') ? 'TapForNerd' : (data.artist || 'Unknown');
            const cleanTitle = (data.title || 'Untitled').replace(/\.(mp3|wav|m4a|mp4|ogg|webm|flac|aac)$/i, '');
            document.getElementById('songTitle').textContent = `${cleanTitle} - ${artist}`;
            
            // Ensure file path is properly encoded
            const fileName = data.file_path.split('/').pop();
            if (!fileName) {
                throw new Error('Invalid file path');
            }
            
            const newSrc = `/media/${encodeURIComponent(fileName)}`;
            console.log('Setting new media source:', newSrc);
            
            const ext = fileName.split('.').pop()?.toLowerCase();
            if (!ext) {
                throw new Error('Invalid file extension');
            }
            
            const isVideo = ['mp4', 'webm', 'mkv'].includes(ext);
            
            // Clear existing sources
            this.audioPlayer.src = '';
            this.videoPlayer.src = '';
            
            // Reset error states
            this.audioPlayer.error = null;
            this.videoPlayer.error = null;

            if (isVideo) {
                console.log('Loading video file');
                this.currentMediaType = 'video';
                this.videoPlayer.style.display = 'block';
                this.videoContainer.style.display = 'block';
                this.visualizerContainer.style.display = 'none';
                this.audioPlayer.style.display = 'none';
                if (this.visualizer) {
                    this.visualizer.stop();
                }
                this.videoPlayer.src = newSrc;
                await this.videoPlayer.load();
                console.log('Video loaded');
            } else {
                console.log('Loading audio file');
                this.currentMediaType = 'audio';
                this.videoPlayer.style.display = 'none';
                this.videoContainer.style.display = 'none';
                this.visualizerContainer.style.display = 'block';
                this.audioPlayer.style.display = 'none';
                this.videoPlayer.src = '';
                this.audioPlayer.src = newSrc;
                await this.audioPlayer.load();
                
                if (!this.visualizer) {
                    this.visualizer = new AudioVisualizer();
                }
                
                try {
                    await this.visualizer.cleanup();
                    await this.visualizer.initialize(this.audioPlayer);
                    this.visualizer.switchVisualizer(true);
                } catch (visualizerError) {
                    console.error('Visualizer error:', visualizerError);
                }
                console.log('Audio loaded');
            }
        } catch (error) {
            console.error('Error loading media:', error);
            throw error;
        }
    }

    async playMedia() {
        try {
            console.log('Starting playMedia...');
            const player = this.currentMediaType === 'video' ? this.videoPlayer : this.audioPlayer;
            console.log('Current media type:', this.currentMediaType);
            
            if (!player.src) {
                console.log('No media source set, fetching current track...');
                await this.updateNowPlaying();
                if (!player.src) {
                    throw new Error('No media source available');
                }
            }
            
            if (this.currentMediaType === 'audio') {
                console.log('Initializing audio visualizer...');
                if (!this.visualizer || !this.visualizer.isInitialized) {
                    this.visualizer = new AudioVisualizer();
                }
                
                try {
                    // Ensure audio context is created and resumed before initializing visualizer
                    await this.visualizer.initialize(this.audioPlayer);
                    
                    // Handle suspended audio context state
                    if (this.visualizer.audioContext?.state === 'suspended') {
                        console.log('Audio context is suspended, attempting to resume...');
                        try {
                            await this.visualizer.audioContext.resume();
                            console.log('Audio context resumed successfully');
                        } catch (resumeError) {
                            console.error('Failed to resume audio context:', resumeError);
                            // Continue playback even if visualizer fails
                        }
                    }
                } catch (visualizerError) {
                    console.error('Visualizer initialization error:', visualizerError);
                    // Continue playback even if visualizer fails
                    console.log('Continuing playback without visualizer');
                }
            }
            
            console.log('Waiting for media to be ready...');
            if (player.readyState < 2) {
                await new Promise((resolve, reject) => {
                    player.addEventListener('loadeddata', resolve, { once: true });
                    player.addEventListener('error', reject, { once: true });
                });
            }
            
            console.log('Starting playback...');
            await player.play();
            this.updatePlayPauseIcon();
            
            if (this.currentMediaType === 'audio' && this.visualizer?.isInitialized) {
                this.visualizer.draw();
            }
            console.log('Playback started successfully');
        } catch (error) {
            console.error('Playback error:', error);
            throw error;
        }
    }

    pauseMedia() {
        const player = this.currentMediaType === 'video' ? this.videoPlayer : this.audioPlayer;
        player.pause();
        this.updatePlayPauseIcon();
        if (this.currentMediaType === 'audio' && this.visualizer) {
            this.visualizer.stop();
        }
    }

    startContinuousPlayback() {
        console.log('Starting continuous playback monitoring...');
        if (this.playbackMonitor) {
            clearInterval(this.playbackMonitor);
        }
        
        this.playbackMonitor = setInterval(() => {
            const player = this.currentMediaType === 'video' ? this.videoPlayer : this.audioPlayer;
            if (!player.paused && !this.isTransitioning) {
                this.updateNowPlaying();
            }
        }, 10000);
    }

    async updateNowPlaying() {
        try {
            console.log('Fetching current track...');
            const response = await fetch('/api/now-playing');
            const data = await response.json();
            
            if (data.error) {
                console.log('No current track:', data.error);
                return;
            }
            
            await this.loadMedia(data);
            this.updateNextTrack();
            return true;
        } catch (error) {
            console.error('Error updating now playing:', error);
            return false;
        }
    }

    toggleFullScreen() {
        const fullscreenIcon = document.getElementById('fullscreenIcon');
        
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen()
                .then(() => {
                    fullscreenIcon.classList.remove('fa-expand');
                    fullscreenIcon.classList.add('fa-compress');
                })
                .catch(err => {
                    console.error('Error attempting to enable fullscreen:', err);
                });
        } else {
            document.exitFullscreen()
                .then(() => {
                    fullscreenIcon.classList.remove('fa-compress');
                    fullscreenIcon.classList.add('fa-expand');
                })
                .catch(err => {
                    console.error('Error attempting to exit fullscreen:', err);
                });
        }
    }

    async initialize() {
        try {
            console.log('Initializing media display...');
            this.visualizer = new AudioVisualizer();
            
            // Hide the start playback button since we're auto-playing
            document.getElementById('startPlayback').classList.add('hidden');
            
            // Start the playlist if playlist ID is in URL
            const urlParams = new URLSearchParams(window.location.search);
            const playlistId = urlParams.get('playlist');
            
            console.log('Initializing playlist...');
            const playResponse = await fetch('/api/play', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ playlist_id: playlistId || null })
            });
            
            if (!playResponse.ok) {
                throw new Error(`Failed to initialize playlist: ${playResponse.status}`);
            }
            
            await playResponse.json();
            
            // Get current track info
            console.log('Fetching initial track info...');
            const response = await fetch('/api/now-playing');
            if (!response.ok) {
                throw new Error(`Failed to fetch current track: ${response.status}`);
            }
            
            const data = await response.json();
            if (data.error) {
                console.error('No media available:', data.error);
                // Show a message to the user that no media is available
                document.getElementById('songTitle').textContent = 'No media available';
                document.getElementById('nextUpSong').textContent = 'Playlist empty';
                return;
            }
            
            console.log('Initial track info received:', data);
            await this.loadMedia(data);
            await this.playMedia();
            this.startContinuousPlayback();
            this.updateNextTrack();
        } catch (error) {
            console.error('Error during initialization:', error);
            setTimeout(async () => {
                try {
                    console.log('Retrying initialization...');
                    this.visualizer = new AudioVisualizer();
                    await fetch('/api/play', { method: 'POST' });
                    const response = await fetch('/api/now-playing');
                    const data = await response.json();
                    
                    if (!data.error) {
                        await this.loadMedia(data);
                        await this.playMedia();
                        this.startContinuousPlayback();
                    }
                } catch (retryError) {
                    console.error('Retry failed:', retryError);
                }
            }, 1000);
        }
    }
}
