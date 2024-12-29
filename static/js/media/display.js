import { MediaPlayer } from './player.js';
import { MediaState } from './state.js';
import { MediaVisualizer } from './visualizer.js';
import { MediaControls } from './controls.js';

export class MediaDisplay {
    constructor() {
        console.log('Initializing MediaDisplay...');
        this.player = new MediaPlayer();
        this.state = new MediaState();
        this.visualizer = new MediaVisualizer();
        this.controls = new MediaControls(this.player, this.state);
        this.isTransitioning = false;
        this.currentTrack = null;

        this.initializeEventListeners();
        this.initialize();
    }

    initializeEventListeners() {
        // Handle media ended events
        this.player.addEndedListener(async () => {
            if (this.isTransitioning) {
                console.log('Already transitioning, skipping duplicate ended event');
                return;
            }
            
            const isVideo = this.state.getMediaType() === 'video';
            const player = isVideo ? this.player.videoPlayer : this.player.audioPlayer;
            
            // Only handle ended event if we're actually near the end
            if (player.currentTime < player.duration - 1) {
                console.log('Ignoring ended event - not near end of track');
                return;
            }
            
            console.log('Media ended, transitioning to next track...');
            this.isTransitioning = true;
            
            try {
                // Stop visualizer but don't clean up yet
                this.visualizer.stop();
                
                // Clear current track reference
                this.currentTrack = null;
                
                await this.handleNextTrack();
            } catch (error) {
                console.error('Error during track transition:', error);
                // Wait longer before retrying
                setTimeout(() => this.handleNextTrack(), 2000);
            } finally {
                setTimeout(() => {
                    this.isTransitioning = false;
                }, 1000);
            }
        });

        // Handle window messages
        window.addEventListener('message', async (event) => {
            console.log('Received message:', event.data);
            if (event.data === 'play') {
                try {
                    await this.updateAndPlay();
                } catch (error) {
                    console.error('Error starting playback:', error);
                    setTimeout(() => this.updateAndPlay(), 2000);
                }
            } else if (event.data === 'pause') {
                this.pause();
            } else if (event.data === 'togglePlay') {
                await this.controls.togglePlay();
            } else if (event.data === 'mute') {
                this.player.setMuted(true);
            } else if (event.data.type === 'updateText') {
                if (event.data.target === 'marquee') {
                    document.getElementById('marqueeText').textContent = event.data.text;
                } else if (event.data.target === 'footer') {
                    document.getElementById('footer').textContent = event.data.text;
                }
            }
        });

        // Start playback button
        const startButton = document.getElementById('startPlayback');
        if (startButton) {
            startButton.addEventListener('click', async () => {
                try {
                    await this.updateAndPlay();
                    this.controls.hideStartPlayback();
                } catch (error) {
                    console.error('Error starting playback:', error);
                }
            }, { once: true });
        }
    }

    async initialize() {
        try {
            console.log('Starting initialization...');
            this.controls.hideStartPlayback();
            
            // Start the playlist if playlist ID is in URL
            const urlParams = new URLSearchParams(window.location.search);
            const playlistId = urlParams.get('playlist');
            
            console.log('Starting playback...');
            
            // Start playback and wait for it to complete
            try {
                await this.state.startPlayback(playlistId || null);
                console.log('Playlist started successfully');
            } catch (error) {
                console.error('Failed to start playlist:', error);
                this.controls.updateTrackInfo('Error', 'Failed to load playlist');
                throw error;
            }
            
            // Add a delay to ensure backend has processed the playlist
            console.log('Waiting for backend to process...');
            await new Promise(resolve => setTimeout(resolve, 2000));
            
            // Load and play initial track
            console.log('Fetching initial track...');
            const track = await this.state.fetchCurrentTrack();
            
            if (!track || !track.source) {
                console.error('Invalid track data:', track);
                this.controls.updateTrackInfo('No media available', 'Please check playlist');
                this.controls.updateNextTrack('End of playlist', '');
                return;
            }
            
            console.log('Initial track loaded:', track);
            await this.loadAndPlay(track);
        } catch (error) {
            console.error('Error during initialization:', error);
            // Wait longer before retrying
            setTimeout(() => this.initialize(), 2000);
        }
    }

    async loadAndPlay(track) {
        if (!track) {
            console.error('No track provided to loadAndPlay');
            return;
        }

        // Skip if trying to load the same track
        if (this.currentTrack && this.currentTrack.source === track.source) {
            console.log('Track already loaded:', track.title);
            return;
        }

        console.log('Loading track:', track);
        this.controls.updateTrackInfo(track.title, track.artist);
        
        try {
            // Update media type first
            this.state.setMediaType(track.isVideo);
            
            // Load media and wait for it to be ready
            await this.player.loadMedia(track.source, track.isVideo);
            
            // Start playback first for audio tracks
            if (!track.isVideo) {
                await this.player.play(track.isVideo);
                
                // Set up visualizer after playback has started
                try {
                    console.log('Setting up audio visualizer...');
                    await this.visualizer.initialize(this.player.audioPlayer);
                    console.log('Audio visualizer setup complete');
                } catch (error) {
                    console.error('Error initializing visualizer:', error);
                    // Continue even if visualizer fails
                }
            } else {
                // For video, just start playback
                await this.player.play(track.isVideo);
            }
            this.controls.updatePlayPauseIcon();
            
            // Store current track reference
            this.currentTrack = track;
            
            // Start visualizer if it was initialized successfully
            if (!track.isVideo && this.visualizer.isVisualizerInitialized()) {
                console.log('Starting visualizer animation');
                this.visualizer.draw();
            }
            
            // Update next track info
            const nextTrack = await this.state.fetchNextTrack();
            if (nextTrack) {
                this.controls.updateNextTrack(nextTrack.title, nextTrack.artist);
            }
            
        } catch (error) {
            console.error('Error in loadAndPlay:', error);
            // Try to recover by moving to next track after a delay
            setTimeout(() => this.handleNextTrack(), 2000);
        }
    }

    async handleNextTrack() {
        console.log('Handling next track...');
        try {
            // Clean up visualizer before loading next track
            await this.visualizer.cleanup();
            
            const track = await this.state.nextTrack();
            if (track) {
                console.log('Next track found:', track);
                await this.loadAndPlay(track);
            } else {
                console.log('No next track available');
                this.pause();
                this.controls.updatePlayPauseIcon();
            }
        } catch (error) {
            console.error('Error in handleNextTrack:', error);
            // Wait a bit and try again
            setTimeout(() => this.handleNextTrack(), 2000);
        }
    }

    async updateAndPlay() {
        const track = await this.state.fetchCurrentTrack();
        if (track) {
            await this.loadAndPlay(track);
        }
    }

    async pause() {
        const isVideo = this.state.getMediaType() === 'video';
        this.player.pause(isVideo);
        if (!isVideo) {
            this.visualizer.stop(); // Just stop animation, don't cleanup
        }
    }
}

// Initialize the media display after DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    console.log('DOM loaded, initializing MediaDisplay...');
    new MediaDisplay();
});
