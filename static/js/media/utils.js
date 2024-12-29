export function formatTime(seconds) {
    const minutes = Math.floor(seconds / 60);
    const remainingSeconds = Math.floor(seconds % 60);
    return `${minutes}:${remainingSeconds.toString().padStart(2, '0')}`;
}

export function cleanTitle(title) {
    return title.replace(/\.(mp3|wav|m4a|mp4|ogg|webm|flac|aac)$/i, '');
}

export function getArtistName(artist) {
    return artist.toLowerCase().includes('unknown artist') ? 'TapForNerd' : artist;
}

export function isVideoFile(filename) {
    const ext = filename.split('.').pop().toLowerCase();
    return ['mp4', 'webm', 'mkv'].includes(ext);
}

export function getMediaSource(filePath) {
    if (!filePath || typeof filePath !== 'string') {
        console.error('Invalid file path:', filePath);
        throw new Error('Invalid file path: path must be a non-empty string');
    }

    // Remove any leading/trailing whitespace and slashes
    const cleanPath = filePath.trim().replace(/^\/+|\/+$/g, '');
    
    if (!cleanPath) {
        console.error('Empty file path after cleaning');
        throw new Error('Invalid file path: path is empty after cleaning');
    }

    try {
        // Handle paths that might be in subdirectories
        const parts = cleanPath.split('/').filter(part => part.trim());
        
        if (parts.length === 0) {
            console.error('No valid path parts found');
            throw new Error('Invalid file path: no valid parts');
        }

        const mediaIndex = parts.indexOf('media');
        let relativePath;
        
        if (mediaIndex !== -1) {
            // If path contains 'media', keep everything after it
            relativePath = parts.slice(mediaIndex + 1).join('/');
            if (!relativePath) {
                console.error('No path components after media directory');
                throw new Error('Invalid file path: no components after media directory');
            }
        } else {
            // If no media directory in path, just use the filename
            relativePath = parts[parts.length - 1];
        }

        // Validate filename
        if (!/\.[a-zA-Z0-9]+$/.test(relativePath)) {
            console.error('Invalid filename - missing or invalid extension:', relativePath);
            throw new Error('Invalid file path: missing or invalid file extension');
        }

        // Construct and validate the final URL
        const mediaUrl = `/media/${encodeURIComponent(relativePath)}`;
        try {
            new URL(mediaUrl, window.location.origin);
        } catch (error) {
            console.error('Invalid media URL:', mediaUrl);
            throw new Error('Invalid file path: results in invalid URL');
        }

        return mediaUrl;
    } catch (error) {
        console.error('Error processing media path:', error);
        throw error;
    }
}
