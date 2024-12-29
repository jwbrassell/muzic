export class PlayerUI {
    constructor() {
        this.playPauseIcon = document.getElementById('playPauseIcon');
        this.fullscreenIcon = document.getElementById('fullscreenIcon');
        this.songTitle = document.getElementById('songTitle');
        this.nextUpSong = document.getElementById('nextUpSong');
        this.progressFill = document.getElementById('progressFill');
        this.currentTime = document.getElementById('currentTime');
        this.duration = document.getElementById('duration');
    }

    updatePlayPauseIcon(isPaused) {
        this.playPauseIcon.classList.remove('fa-play', 'fa-pause');
        this.playPauseIcon.classList.add(isPaused ? 'fa-play' : 'fa-pause');
    }

    updateProgress(currentTime, duration) {
        if (!duration) return;
        
        const progress = (currentTime / duration) * 100;
        this.progressFill.style.width = `${progress}%`;
        this.currentTime.textContent = this.formatTime(currentTime);
        this.duration.textContent = this.formatTime(duration);
    }

    updateSongTitle(artist, title) {
        const cleanTitle = title.replace(/\.(mp3|wav|m4a|mp4|ogg|webm|flac|aac)$/i, '');
        const displayArtist = artist.toLowerCase().includes('unknown artist') ? 'TapForNerd' : artist;
        this.songTitle.textContent = `${cleanTitle} - ${displayArtist}`;
    }

    updateNextTrack(artist, title) {
        if (!title) {
            this.nextUpSong.textContent = 'End of playlist';
            return;
        }
        const cleanTitle = title.replace(/\.(mp3|wav|m4a|mp4|ogg|webm|flac|aac)$/i, '');
        const displayArtist = artist.toLowerCase().includes('unknown artist') ? 'TapForNerd' : artist;
        this.nextUpSong.textContent = `${cleanTitle} - ${displayArtist}`;
    }

    formatTime(seconds) {
        const minutes = Math.floor(seconds / 60);
        const remainingSeconds = Math.floor(seconds % 60);
        return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
    }

    updateFullscreenIcon(isFullscreen) {
        this.fullscreenIcon.classList.remove('fa-expand', 'fa-compress');
        this.fullscreenIcon.classList.add(isFullscreen ? 'fa-compress' : 'fa-expand');
    }

    updateMarquee(text) {
        document.getElementById('marqueeText').textContent = text;
    }

    updateFooter(text) {
        document.getElementById('footer').textContent = text;
    }
}

export const ui = new PlayerUI();
