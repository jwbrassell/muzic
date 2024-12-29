import { AudioVisualizer } from './visualizer.js';
import { ui } from './ui.js';

class Player {
    constructor() {
        this.audio = document.getElementById('audioPlayer');
        this.isRepeat = true;
        this.isShuffle = false;
        this.isTransitioning = false;
        this.playbackMonitor = null;
        this.visualizer = null;

        this.audio.preload = 'auto';
        this.audio.loop = false;

        // Update progress every 100ms
        setInterval(() => this.updateProgress(), 100);
    }

    async initializeVisualizer() {
        if (!this.visualizer) {
            this.visualizer = new AudioVisualizer();
            await this.visualizer.initialize(this.audio);
            this.visualizer.switchVisualizer(true);
        }
    }

    updateProgress() {
        ui.updateProgress(this.audio.currentTime, this.audio.duration);
    }

    seekTo(position) {
        this.audio.currentTime = position * this.audio.duration;
    }

    async togglePlay() {
        if (this.audio.paused) {
            await this.play();
        } else {
            this.pause();
        }
    }

    async play() {
        try {
            if (!this.audio.src) {
                console.log('No audio source set, fetching current track...');
                await this.updateNowPlaying();
                if (!this.audio.src) {
                    throw new Error('No audio source available');
                }
            }

            if (!this.visualizer?.isInitialized) {
                await this.initializeVisualizer();
            }

            if (this.visualizer?.audioContext?.state === 'suspended') {
                await this.visualizer.audioContext.resume();
            }

            if (this.audio.readyState < 2) {
                await new Promise((resolve, reject) => {
                    this.audio.addEventListener('loadeddata', resolve, { once: true });
                    this.audio.addEventListener('error', reject, { once: true });
                });
            }

            await this.audio.play();
            ui.updatePlayPauseIcon(false);

            if (this.visualizer?.isInitialized) {
                this.visualizer.draw();
            }
        } catch (error) {
            console.error('Playback error:', error);
            throw error;
        }
    }

    pause() {
        this.audio.pause();
        ui.updatePlayPauseIcon(true);
        if (this.visualizer) {
            this.visualizer.stop();
        }
    }

    mute() {
        this.audio.muted = true;
    }

    async handlePlayCommand() {
        try {
            await this.updateNowPlaying();
            await this.play();
            this.startContinuousPlayback();
        } catch (error) {
            console.error('Error starting playback:', error);
            setTimeout(async () => {
                await this.updateNowPlaying();
                await this.play();
                this.startContinuousPlayback();
            }, 1000);
        }
    }

    async handleTrackEnd() {
        if (this.isTransitioning) {
            console.log('Already transitioning, skipping duplicate ended event');
            return;
        }

        console.log('Audio ended, transitioning to next track...');
        this.isTransitioning = true;

        try {
            await this.nextTrack();
            if (!this.isRepeat) {
                const response = await fetch('/api/now-playing');
                const data = await response.json();
                if (data.error) {
                    this.pause();
                    this.audio.src = '';
                    ui.updatePlayPauseIcon(true);
                }
            }
        } catch (error) {
            console.error('Error during track transition:', error);
            setTimeout(() => this.nextTrack(), 1000);
        } finally {
            setTimeout(() => {
                this.isTransitioning = false;
            }, 500);
        }
    }

    handleError(e) {
        const error = this.audio.error;
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
            console.error('Audio error:', errorMessage, error.message);

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
            console.error('Audio error event without error details:', e);
        }
    }

    startContinuousPlayback() {
        console.log('Starting continuous playback monitoring...');
        if (this.playbackMonitor) {
            clearInterval(this.playbackMonitor);
        }

        this.playbackMonitor = setInterval(() => {
            if (!this.audio.paused && !this.isTransitioning) {
                this.updateNowPlaying();
            }
        }, 10000);
    }

    async updateNextTrack() {
        try {
            const response = await fetch('/api/next-track');
            const data = await response.json();
            if (!data.error) {
                ui.updateNextTrack(data.artist, data.title);
            } else {
                ui.updateNextTrack(null, null);
            }
        } catch (error) {
            console.error('Error fetching next track:', error);
            ui.updateNextTrack(null, null);
        }
    }

    async updateNowPlaying() {
        try {
            const response = await fetch('/api/now-playing');
            const data = await response.json();
            
            if (!data.error) {
                ui.updateSongTitle(data.artist, data.title);
                const newSrc = `/media/${encodeURIComponent(data.file_path.split('/').pop())}`;
                
                if (this.audio.src !== window.location.origin + newSrc) {
                    this.audio.src = newSrc;
                    await this.audio.load();
                    await this.initializeVisualizer();
                }
            }
        } catch (error) {
            console.error('Error:', error);
        }
    }

    async nextTrack() {
        try {
            this.pause();
            const response = await fetch('/api/next', { method: 'POST' });
            const data = await response.json();
            
            if (data.error) {
                if (this.isRepeat) {
                    await this.updateNowPlaying();
                }
                return;
            }

            ui.updateSongTitle(data.artist, data.title);
            const newSrc = `/media/${encodeURIComponent(data.file_path.split('/').pop())}`;
            
            if (this.audio.src !== window.location.origin + newSrc) {
                this.audio.src = newSrc;
                await this.audio.load();
                await this.initializeVisualizer();
                await this.play();
                this.updateNextTrack();
            }
        } catch (error) {
            console.error('Error during track transition:', error);
            setTimeout(() => this.nextTrack(), 1000);
        }
    }
}

export const player = new Player();
