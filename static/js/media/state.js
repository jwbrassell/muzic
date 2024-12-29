import { cleanTitle, getArtistName, getMediaSource, isVideoFile } from './utils.js';

export class MediaState {
    constructor() {
        this.isRepeat = true;
        this.isShuffle = false;
        this.currentMediaType = null;
        this.isTransitioning = false;
    }

    async fetchCurrentTrack() {
        try {
            console.log('Fetching current track...');
            const response = await fetch('/api/now-playing');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            if (data.error) {
                console.log('No current track:', data.error);
                return null;
            }

            if (!data.file_path) {
                console.error('Invalid track data - missing file_path:', data);
                return null;
            }

            const track = this.formatTrackData(data);
            console.log('Current track data:', track);
            return track;
        } catch (error) {
            console.error('Error fetching current track:', error);
            return null;
        }
    }

    async fetchNextTrack() {
        try {
            console.log('Fetching next track info...');
            const response = await fetch('/api/next-track');
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            if (!data.error) {
                if (!data.file_path) {
                    console.error('Invalid next track data - missing file_path:', data);
                    return null;
                }
                const track = this.formatTrackData(data);
                console.log('Next track info:', track);
                return track;
            }
            console.log('No next track available');
            return null;
        } catch (error) {
            console.error('Error fetching next track:', error);
            return null;
        }
    }

    async startPlayback(playlistId = null) {
        try {
            if (playlistId) {
                console.log('Starting playlist:', playlistId);
                const response = await fetch('/api/play', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ playlist_id: playlistId })
                });
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            } else {
                console.log('Starting default playback');
                const response = await fetch('/api/play', { method: 'POST' });
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
            }
            console.log('Playback started successfully');
        } catch (error) {
            console.error('Error starting playback:', error);
            throw error;
        }
    }

    async nextTrack() {
        try {
            console.log('Requesting next track...');
            const response = await fetch('/api/next', { method: 'POST' });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            
            if (data.error) {
                console.log('End of playlist reached or error:', data.error);
                if (this.isRepeat) {
                    console.log('Repeat is on, restarting playlist');
                    await this.startPlayback(); // Restart playlist from beginning
                    await new Promise(resolve => setTimeout(resolve, 500)); // Wait for backend to process
                    return await this.fetchCurrentTrack();
                }
                return null;
            }

            if (!data.file_path) {
                console.error('Invalid next track data - missing file_path:', data);
                return null;
            }

            const track = this.formatTrackData(data);
            console.log('Next track data:', track);
            return track;
        } catch (error) {
            console.error('Error in nextTrack:', error);
            throw error;
        }
    }

    formatTrackData(data) {
        if (!data || !data.file_path) {
            console.error('Invalid track data:', data);
            throw new Error('Invalid track data - missing file_path');
        }

        const source = getMediaSource(data.file_path);
        if (!source) {
            console.error('Invalid media source path:', data.file_path);
            throw new Error('Invalid media source path');
        }

        console.log('Formatting track data:', {
            title: data.title,
            artist: data.artist,
            file_path: data.file_path,
            source: source
        });

        return {
            title: cleanTitle(data.title),
            artist: getArtistName(data.artist),
            source: source,
            isVideo: isVideoFile(data.file_path),
            originalPath: data.file_path // Keep original path for debugging
        };
    }

    async saveState() {
        try {
            const response = await fetch('/api/save-state', { method: 'POST' });
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            const data = await response.json();
            console.log('Playlist state saved:', data);
            return true;
        } catch (error) {
            console.error('Error saving playlist state:', error);
            return false;
        }
    }

    setMediaType(isVideo) {
        this.currentMediaType = isVideo ? 'video' : 'audio';
    }

    getMediaType() {
        return this.currentMediaType;
    }

    setTransitioning(value) {
        this.isTransitioning = value;
    }

    isMediaTransitioning() {
        return this.isTransitioning;
    }
}
