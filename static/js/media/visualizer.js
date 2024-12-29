import { AudioVisualizer } from '../visualizer.js';

export class MediaVisualizer {
    constructor() {
        this.visualizer = null;
        this.isInitialized = false;
        this.currentAudioPlayer = null;
        this.initializationInProgress = false;
        this.initializationPromise = null;
    }

    async initialize(audioPlayer) {
        // If initialization is in progress, wait for it to complete
        if (this.initializationPromise) {
            console.log('Waiting for existing initialization to complete...');
            try {
                await this.initializationPromise;
            } catch (error) {
                console.error('Previous initialization failed:', error);
            }
        }

        // Create new initialization promise
        this.initializationPromise = this._initialize(audioPlayer);
        
        try {
            await this.initializationPromise;
        } finally {
            this.initializationPromise = null;
        }
    }

    async _initialize(audioPlayer) {
        // Prevent concurrent initialization
        if (this.initializationInProgress) {
            console.log('Initialization already in progress, skipping...');
            return;
        }
        
        this.initializationInProgress = true;
        console.log('Initializing media visualizer...');
        
        try {
            // If we already have a visualizer and it's for the same audio player,
            // just ensure it's properly connected
            if (this.visualizer && this.currentAudioPlayer === audioPlayer) {
                console.log('Reinitializing existing visualizer');
                await this.visualizer.initialize(audioPlayer);
                this.isInitialized = true;
                return;
            }
            
            // Clean up existing visualizer if switching to a new audio player
            if (this.currentAudioPlayer !== audioPlayer) {
                await this.cleanup();
            }
            
            // Create new visualizer if needed
            if (!this.visualizer) {
                console.log('Creating new AudioVisualizer instance');
                this.visualizer = new AudioVisualizer();
            }
            
            // Initialize with audio player
            console.log('Initializing visualizer with audio player');
            await this.visualizer.initialize(audioPlayer);
            
            this.currentAudioPlayer = audioPlayer;
            this.visualizer.switchVisualizer(true);
            this.isInitialized = true;
            console.log('Media visualizer initialized successfully');
            
        } catch (error) {
            console.error('Media visualizer initialization error:', error);
            this.isInitialized = false;
            this.currentAudioPlayer = null;
            await this.cleanup();
            throw error;
        } finally {
            this.initializationInProgress = false;
        }
    }

    draw() {
        if (this.isInitialized && this.visualizer) {
            this.visualizer.draw();
        }
    }

    stop() {
        if (this.visualizer) {
            this.visualizer.stop();
        }
    }

    async cleanup() {
        console.log('Cleaning up media visualizer...');
        
        this.initializationInProgress = false;
        this.initializationPromise = null;
        
        if (this.visualizer) {
            try {
                // Stop any ongoing animation
                this.stop();
                
                // Clean up the visualizer
                await this.visualizer.cleanup();
                this.visualizer = null;
                
                console.log('Visualizer cleanup complete');
            } catch (error) {
                console.error('Error during visualizer cleanup:', error);
            }
        }
        
        this.isInitialized = false;
        this.currentAudioPlayer = null;
        console.log('Media visualizer cleanup complete');
    }

    switchVisualizer(enabled) {
        if (this.visualizer) {
            this.visualizer.switchVisualizer(enabled);
        }
    }

    getAudioContext() {
        return this.visualizer?.audioContext;
    }

    isVisualizerInitialized() {
        return this.isInitialized && this.visualizer !== null;
    }
}
