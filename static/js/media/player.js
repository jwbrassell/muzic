export class MediaPlayer {
    constructor() {
        this.audioPlayer = document.getElementById('audioPlayer');
        this.videoPlayer = document.getElementById('videoPlayer');
        this.visualizerContainer = document.getElementById('visualizerContainer');
        this.videoContainer = document.getElementById('videoContainer');

        // Initialize players
        [this.audioPlayer, this.videoPlayer].forEach(player => {
            player.preload = 'auto';
            player.loop = false;
            player.autoplay = false; // Disable autoplay initially
            player.muted = false;
            player.controls = false; // Use custom controls
        });

        // Add comprehensive media event listeners
        [this.audioPlayer, this.videoPlayer].forEach(player => {
            const type = player === this.videoPlayer ? 'Video' : 'Audio';

            // Loading events
            player.addEventListener('loadstart', () => console.log(`${type} loadstart`));
            player.addEventListener('durationchange', () => console.log(`${type} duration changed to:`, player.duration));
            player.addEventListener('loadedmetadata', () => console.log(`${type} metadata loaded, duration:`, player.duration));
            player.addEventListener('loadeddata', () => console.log(`${type} data loaded, ready state:`, player.readyState));
            player.addEventListener('progress', () => console.log(`${type} progress event`));
            player.addEventListener('canplay', () => console.log(`${type} can start playing`));
            player.addEventListener('canplaythrough', () => console.log(`${type} can play through`));

            // Playback events
            player.addEventListener('play', () => console.log(`${type} play event`));
            player.addEventListener('playing', () => console.log(`${type} playing event`));
            player.addEventListener('pause', () => console.log(`${type} pause event`));
            player.addEventListener('seeking', () => console.log(`${type} seeking to:`, player.currentTime));
            player.addEventListener('seeked', () => console.log(`${type} seeked to:`, player.currentTime));
            player.addEventListener('ratechange', () => console.log(`${type} playback rate:`, player.playbackRate));
            player.addEventListener('timeupdate', () => {
                if (Math.floor(player.currentTime) % 5 === 0) { // Log every 5 seconds
                    console.log(`${type} time:`, player.currentTime, '/', player.duration);
                }
            });

            // End events
            player.addEventListener('ended', () => {
                console.log(`${type} ended:`, {
                    currentTime: player.currentTime,
                    duration: player.duration,
                    readyState: player.readyState,
                    networkState: player.networkState,
                    error: player.error
                });
            });

            // Error events
            player.addEventListener('error', (e) => {
                console.error(`${type} error:`, {
                    error: e.target.error,
                    currentTime: player.currentTime,
                    duration: player.duration,
                    readyState: player.readyState,
                    networkState: player.networkState,
                    src: player.src
                });
            });

            // Stall events
            player.addEventListener('waiting', () => console.log(`${type} waiting for data`));
            player.addEventListener('suspend', () => console.log(`${type} suspended`));
            player.addEventListener('stalled', () => console.log(`${type} stalled`));
            player.addEventListener('emptied', () => console.log(`${type} emptied`));
        });
    }

    async loadMedia(source, isVideo) {
        console.log(`Loading ${isVideo ? 'video' : 'audio'} file:`, source);
        
        // Reset both players
        this.cleanup();
        
        // Get the active player
        const player = isVideo ? this.videoPlayer : this.audioPlayer;
        
        // Validate source URL
        if (!source || typeof source !== 'string') {
            throw new Error('Invalid media source: source must be a non-empty string');
        }

        try {
            new URL(source, window.location.origin);
        } catch (error) {
            throw new Error('Invalid media source: malformed URL');
        }

        // Set up loading promise before changing source
        const loadPromise = new Promise((resolve, reject) => {
            let resolved = false;
            
            const loadedDataHandler = () => {
                console.log(`${isVideo ? 'Video' : 'Audio'} data loaded`);
                if (!resolved && player.readyState >= 2) {
                    resolved = true;
                    cleanup();
                    resolve();
                }
            };
            
            const canPlayHandler = () => {
                console.log(`${isVideo ? 'Video' : 'Audio'} can play`);
                if (!resolved && player.readyState >= 3) {
                    resolved = true;
                    cleanup();
                    resolve();
                }
            };
            
            const errorHandler = (event) => {
                const error = event.target.error;
                let errorMessage = 'Unknown error';
                
                if (error) {
                    switch (error.code) {
                        case MediaError.MEDIA_ERR_ABORTED:
                            errorMessage = 'Loading aborted';
                            break;
                        case MediaError.MEDIA_ERR_NETWORK:
                            errorMessage = 'Network error';
                            break;
                        case MediaError.MEDIA_ERR_DECODE:
                            errorMessage = 'Media decode error';
                            break;
                        case MediaError.MEDIA_ERR_SRC_NOT_SUPPORTED:
                            errorMessage = 'Media format not supported';
                            break;
                    }
                }
                
                console.error(`Error loading ${isVideo ? 'video' : 'audio'}: ${errorMessage}`, error);
                if (!resolved) {
                    resolved = true;
                    cleanup();
                    reject(new Error(`Failed to load media: ${errorMessage}`));
                }
            };
            
            const cleanup = () => {
                player.removeEventListener('loadeddata', loadedDataHandler);
                player.removeEventListener('canplay', canPlayHandler);
                player.removeEventListener('error', errorHandler);
            };
            
            player.addEventListener('loadeddata', loadedDataHandler);
            player.addEventListener('canplay', canPlayHandler);
            player.addEventListener('error', errorHandler);
            
            // Timeout after 15 seconds
            setTimeout(() => {
                if (!resolved) {
                    resolved = true;
                    cleanup();
                    reject(new Error('Timeout loading media'));
                }
            }, 15000);
        });
        
        // Update display settings
        if (isVideo) {
            this.videoPlayer.style.display = 'block';
            this.videoContainer.style.display = 'block';
            this.visualizerContainer.style.display = 'none';
            this.audioPlayer.style.display = 'none';
        } else {
            this.videoPlayer.style.display = 'none';
            this.videoContainer.style.display = 'none';
            this.visualizerContainer.style.display = 'block';
            this.audioPlayer.style.display = 'none';
        }
        
        // Set source and trigger load
        if (!source) {
            throw new Error('Invalid media source: source is empty');
        }
        
        console.log(`Setting ${isVideo ? 'video' : 'audio'} source to:`, source);
        player.src = source;
        
        // Force a clean load
        try {
            player.load();
        } catch (error) {
            console.error('Error during load:', error);
            throw error;
        }
        
        // Wait for media to load
        try {
            await loadPromise;
            
            // Double check we have valid duration
            if (!player.duration || isNaN(player.duration) || player.duration === 0) {
                throw new Error('Invalid media duration after loading');
            }
            
            console.log(`${isVideo ? 'Video' : 'Audio'} ready to play, duration:`, player.duration);
        } catch (error) {
            console.error('Media load failed:', error);
            throw error;
        }
    }

    async play(isVideo) {
        const player = isVideo ? this.videoPlayer : this.audioPlayer;
        
        // Wait for metadata to be loaded
        if (player.readyState < 2) {
            await new Promise((resolve, reject) => {
                const loadHandler = () => {
                    cleanup();
                    resolve();
                };
                const errorHandler = (error) => {
                    cleanup();
                    reject(error);
                };
                const stalledHandler = () => {
                    // Don't reject on stall, just log it
                    console.log('Playback stalled, waiting...');
                };
                const cleanup = () => {
                    player.removeEventListener('loadeddata', loadHandler);
                    player.removeEventListener('canplay', loadHandler);
                    player.removeEventListener('error', errorHandler);
                    player.removeEventListener('stalled', stalledHandler);
                };
                
                // Listen for either loadeddata or canplay
                player.addEventListener('loadeddata', loadHandler);
                player.addEventListener('canplay', loadHandler);
                player.addEventListener('error', errorHandler);
                player.addEventListener('stalled', stalledHandler);
                
                // Timeout after 10 seconds
                setTimeout(() => {
                    cleanup();
                    reject(new Error('Timeout waiting for media to load'));
                }, 10000);
            });
        }
        
        // Don't throw on invalid duration, just log it
        if (!player.duration || isNaN(player.duration) || player.duration === 0) {
            console.warn('Warning: Invalid media duration before play');
        }
        
        // Log the duration
        console.log(`Starting playback of ${isVideo ? 'video' : 'audio'}:`, {
            duration: player.duration,
            readyState: player.readyState,
            networkState: player.networkState,
            src: player.src
        });
        
        try {
            const playPromise = player.play();
            if (playPromise) {
                await playPromise;
                console.log(`${isVideo ? 'Video' : 'Audio'} playback started successfully`);
            }
        } catch (error) {
            console.error(`Error starting ${isVideo ? 'video' : 'audio'} playback:`, {
                error,
                duration: player.duration,
                readyState: player.readyState,
                networkState: player.networkState
            });
            throw error;
        }
    }

    pause(isVideo) {
        const player = isVideo ? this.videoPlayer : this.audioPlayer;
        player.pause();
    }

    getCurrentTime(isVideo) {
        const player = isVideo ? this.videoPlayer : this.audioPlayer;
        return player.currentTime;
    }

    getDuration(isVideo) {
        const player = isVideo ? this.videoPlayer : this.audioPlayer;
        return player.duration;
    }

    setCurrentTime(time, isVideo) {
        const player = isVideo ? this.videoPlayer : this.audioPlayer;
        player.currentTime = time;
    }

    isPaused(isVideo) {
        const player = isVideo ? this.videoPlayer : this.audioPlayer;
        return player.paused;
    }

    hasSource(isVideo) {
        const player = isVideo ? this.videoPlayer : this.audioPlayer;
        return !!player.src;
    }

    handleMediaError(e) {
        const player = e.target;
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
        } else {
            console.error('Media error event without error details:', e);
        }
    }

    async cleanup() {
        await Promise.all([this.audioPlayer, this.videoPlayer].map(async player => {
            try {
                player.pause();
                player.currentTime = 0;
                const oldSrc = player.src;
                player.src = '';
                player.load(); // Force cleanup
                console.log(`Cleaned up player, old src: ${oldSrc}`);
                
                // Wait for emptied event or timeout
                await Promise.race([
                    new Promise(resolve => {
                        const emptiedHandler = () => {
                            player.removeEventListener('emptied', emptiedHandler);
                            resolve();
                        };
                        player.addEventListener('emptied', emptiedHandler);
                    }),
                    new Promise(resolve => setTimeout(resolve, 1000))
                ]);
            } catch (error) {
                console.error('Error during cleanup:', error);
                // Continue cleanup even if there's an error
            }
        }));
    }

    setMuted(muted) {
        this.audioPlayer.muted = muted;
        this.videoPlayer.muted = muted;
    }

    addEndedListener(callback) {
        [this.audioPlayer, this.videoPlayer].forEach(player => {
            player.addEventListener('ended', callback);
        });
    }

    removeEndedListener(callback) {
        [this.audioPlayer, this.videoPlayer].forEach(player => {
            player.removeEventListener('ended', callback);
        });
    }
}
