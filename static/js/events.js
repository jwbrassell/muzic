import { player } from './player.js';
import { ui } from './ui.js';

export class PlayerEvents {
    constructor() {
        this.setupProgressBarEvents();
        this.setupPlaybackEvents();
        this.setupFullscreenEvents();
        this.setupWindowEvents();
    }

    setupProgressBarEvents() {
        document.getElementById('progressBar').addEventListener('click', (e) => {
            const progressBar = e.currentTarget;
            const clickPosition = (e.pageX - progressBar.offsetLeft) / progressBar.offsetWidth;
            player.seekTo(clickPosition);
        });
    }

    setupPlaybackEvents() {
        document.getElementById('playPauseIcon').addEventListener('click', () => player.togglePlay());

        player.audio.addEventListener('ended', () => player.handleTrackEnd());
        
        player.audio.addEventListener('error', (e) => player.handleError(e));
    }

    setupFullscreenEvents() {
        document.getElementById('fullscreenIcon').addEventListener('click', () => {
            if (!document.fullscreenElement) {
                document.documentElement.requestFullscreen()
                    .then(() => ui.updateFullscreenIcon(true))
                    .catch(err => console.error('Error attempting to enable fullscreen:', err));
            } else {
                document.exitFullscreen()
                    .then(() => ui.updateFullscreenIcon(false))
                    .catch(err => console.error('Error attempting to exit fullscreen:', err));
            }
        });

        document.addEventListener('fullscreenchange', () => {
            ui.updateFullscreenIcon(!!document.fullscreenElement);
        });
    }

    setupWindowEvents() {
        window.addEventListener('message', async (event) => {
            console.log('Received message:', event.data);
            if (event.data === 'play') {
                await player.handlePlayCommand();
            } else if (event.data === 'pause') {
                player.pause();
            } else if (event.data === 'togglePlay') {
                await player.togglePlay();
            } else if (event.data === 'mute') {
                player.mute();
            } else if (event.data.type === 'updateText') {
                if (event.data.target === 'marquee') {
                    ui.updateMarquee(event.data.text);
                } else if (event.data.target === 'footer') {
                    ui.updateFooter(event.data.text);
                }
            }
        });

        window.addEventListener('load', async () => {
            const urlParams = new URLSearchParams(window.location.search);
            const playlistId = urlParams.get('playlist');
            if (playlistId) {
                // Start playlist with the provided ID
                await fetch('/api/play', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ playlist_id: playlistId })
                });
            }
            await player.handlePlayCommand(); // Start playing
            player.startContinuousPlayback();
            player.updateNextTrack();
        });

        // Initialize visualizer on click to handle autoplay restrictions
        document.addEventListener('click', () => player.initializeVisualizer(), { once: true });
    }
}

export const events = new PlayerEvents();
