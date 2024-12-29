import { formatTime } from './utils.js';

export class MediaControls {
    constructor(player, state) {
        this.player = player;
        this.state = state;
        this.playbackMonitor = null;

        // Cache DOM elements
        this.elements = {
            playPauseIcon: document.getElementById('playPauseIcon'),
            fullscreenIcon: document.getElementById('fullscreenIcon'),
            progressBar: document.getElementById('progressBar'),
            progressFill: document.getElementById('progressFill'),
            currentTime: document.getElementById('currentTime'),
            duration: document.getElementById('duration'),
            startPlayback: document.getElementById('startPlayback'),
            songTitle: document.getElementById('songTitle'),
            nextUpSong: document.getElementById('nextUpSong')
        };

        this.initializeEventListeners();
        this.startProgressUpdates();
    }

    initializeEventListeners() {
        // Progress bar click
        this.elements.progressBar.addEventListener('click', (e) => {
            const progressBar = e.currentTarget;
            const clickPosition = (e.pageX - progressBar.offsetLeft) / progressBar.offsetWidth;
            const isVideo = this.state.getMediaType() === 'video';
            this.player.setCurrentTime(clickPosition * this.player.getDuration(isVideo), isVideo);
        });

        // Play/Pause button
        this.elements.playPauseIcon.addEventListener('click', () => this.togglePlay());

        // Fullscreen button
        this.elements.fullscreenIcon.addEventListener('click', () => this.toggleFullScreen());

        // Fullscreen change event
        document.addEventListener('fullscreenchange', () => this.updateFullscreenIcon());
    }

    startProgressUpdates() {
        setInterval(() => this.updateProgress(), 100);
    }

    updateProgress() {
        const isVideo = this.state.getMediaType() === 'video';
        const duration = this.player.getDuration(isVideo);
        if (!duration) return;
        
        const currentTime = this.player.getCurrentTime(isVideo);
        const progress = (currentTime / duration) * 100;
        
        this.elements.progressFill.style.width = `${progress}%`;
        this.elements.currentTime.textContent = formatTime(currentTime);
        this.elements.duration.textContent = formatTime(duration);
    }

    updatePlayPauseIcon() {
        const isVideo = this.state.getMediaType() === 'video';
        const isPaused = this.player.isPaused(isVideo);
        this.elements.playPauseIcon.classList.remove('fa-play', 'fa-pause');
        this.elements.playPauseIcon.classList.add(isPaused ? 'fa-play' : 'fa-pause');
    }

    async togglePlay() {
        const isVideo = this.state.getMediaType() === 'video';
        if (this.player.isPaused(isVideo)) {
            await this.player.play(isVideo);
        } else {
            this.player.pause(isVideo);
        }
        this.updatePlayPauseIcon();
    }

    toggleFullScreen() {
        if (!document.fullscreenElement) {
            document.documentElement.requestFullscreen()
                .catch(err => console.error('Error attempting to enable fullscreen:', err));
        } else {
            document.exitFullscreen()
                .catch(err => console.error('Error attempting to exit fullscreen:', err));
        }
    }

    updateFullscreenIcon() {
        if (document.fullscreenElement) {
            this.elements.fullscreenIcon.classList.remove('fa-expand');
            this.elements.fullscreenIcon.classList.add('fa-compress');
        } else {
            this.elements.fullscreenIcon.classList.remove('fa-compress');
            this.elements.fullscreenIcon.classList.add('fa-expand');
        }
    }

    hideStartPlayback() {
        this.elements.startPlayback.classList.add('hidden');
    }

    updateTrackInfo(title, artist) {
        this.elements.songTitle.textContent = `${title} - ${artist}`;
    }

    updateNextTrack(title, artist) {
        if (title && artist) {
            this.elements.nextUpSong.textContent = `${title} - ${artist}`;
        } else {
            this.elements.nextUpSong.textContent = 'End of playlist';
        }
    }

    startContinuousPlayback(callback) {
        console.log('Starting continuous playback monitoring...');
        if (this.playbackMonitor) {
            clearInterval(this.playbackMonitor);
        }
        
        this.playbackMonitor = setInterval(() => {
            const isVideo = this.state.getMediaType() === 'video';
            if (!this.player.isPaused(isVideo) && !this.state.isMediaTransitioning()) {
                callback();
            }
        }, 10000);
    }

    stopContinuousPlayback() {
        if (this.playbackMonitor) {
            clearInterval(this.playbackMonitor);
            this.playbackMonitor = null;
        }
    }
}
