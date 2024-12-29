import { BarsVisualizer } from './visualizations/bars.js';
import { CirclesVisualizer } from './visualizations/circles.js';
import { WavesVisualizer } from './visualizations/waves.js';
import { FaceVisualizer } from './visualizations/face.js';

class AudioVisualizer {
    constructor() {
        this.audioContext = null;
        this.analyser = null;
        this.source = null;
        this.canvas = document.getElementById('visualizer');
        this.canvasCtx = this.canvas.getContext('2d');
        this.dataArray = null;
        this.animationId = null;
        this.isInitialized = false;
        this.currentVisualizer = null;
        this.visualizerTypes = [BarsVisualizer, CirclesVisualizer, WavesVisualizer, FaceVisualizer];
        this.currentVisualizerIndex = 0;
        this.connectedElement = null;
        
        // Keep track of all audio nodes for proper cleanup
        this.nodes = new Set();
        
        // Add resize listener once during construction
        window.addEventListener('resize', () => this.resizeCanvas());
    }

    async initialize(audioElement) {
        try {
            console.log('Initializing audio visualizer...');
            
            // If we're already connected to this element and context is active, just resume
            if (this.connectedElement === audioElement && 
                this.audioContext && 
                this.source && 
                this.audioContext.state !== 'closed') {
                console.log('Already connected to this audio element');
                if (this.audioContext.state === 'suspended') {
                    await this.audioContext.resume();
                }
                return;
            }
            
            // Clean up existing connections but preserve context if possible
            if (this.source) {
                this.source.disconnect();
                this.source = null;
            }
            
            if (this.analyser) {
                this.analyser.disconnect();
            }
            
            // Create or resume audio context
            if (!this.audioContext || this.audioContext.state === 'closed') {
                this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            } else if (this.audioContext.state === 'suspended') {
                await this.audioContext.resume();
            }
            
            // Create and configure analyser
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            this.dataArray = new Uint8Array(this.analyser.frequencyBinCount);
            
            // Create and connect new source
            console.log('Creating new media element source...');
            this.source = this.audioContext.createMediaElementSource(audioElement);
            
            // Connect nodes: source -> analyser -> destination
            this.source.connect(this.analyser);
            this.analyser.connect(this.audioContext.destination);
            
            // Track all nodes for cleanup
            this.nodes.add(this.source);
            this.nodes.add(this.analyser);
            
            // Store reference to connected element
            this.connectedElement = audioElement;
            
            // Set canvas size
            this.resizeCanvas();
            
            // Initialize or maintain visualizer
            if (!this.currentVisualizer) {
                this.switchVisualizer();
            }
            
            console.log('Audio visualizer initialized successfully');
            this.isInitialized = true;
            this.draw();

        } catch (error) {
            console.error('Error initializing audio context:', error);
            this.isInitialized = false;
            // Attempt cleanup on error
            await this.cleanup();
            throw error;
        }
    }

    resizeCanvas() {
        // Get the container's dimensions
        const container = this.canvas.parentElement;
        this.canvas.width = container.offsetWidth;
        this.canvas.height = container.offsetHeight;
    }

    switchVisualizer(forceNext = false) {
        if (forceNext) {
            // Move to next visualizer
            this.currentVisualizerIndex = (this.currentVisualizerIndex + 1) % this.visualizerTypes.length;
        }
        const VisualizerType = this.visualizerTypes[this.currentVisualizerIndex];
        this.currentVisualizer = new VisualizerType(this.canvas, this.analyser);
    }

    draw() {
        if (!this.isInitialized || !this.currentVisualizer) {
            return;
        }
        
        this.animationId = requestAnimationFrame(() => this.draw());
        try {
            this.currentVisualizer.draw();
        } catch (error) {
            console.error('Error in visualizer draw:', error);
            this.stop();
        }
    }

    stop() {
        if (this.animationId) {
            cancelAnimationFrame(this.animationId);
            this.animationId = null;
        }
    }

    async cleanup() {
        console.log('Cleaning up audio visualizer...');
        this.stop();
        
        // Disconnect nodes but don't close context
        if (this.source) {
            try {
                this.source.disconnect();
            } catch (error) {
                console.error('Error disconnecting source:', error);
            }
            this.source = null;
        }
        
        if (this.analyser) {
            try {
                this.analyser.disconnect();
            } catch (error) {
                console.error('Error disconnecting analyser:', error);
            }
            this.analyser = null;
        }
        
        // Clear other references
        this.connectedElement = null;
        this.dataArray = null;
        this.isInitialized = false;
        
        // Only close audio context if it exists and isn't already closed
        if (this.audioContext && this.audioContext.state !== 'closed') {
            try {
                await this.audioContext.close();
                this.audioContext = null;
            } catch (error) {
                console.error('Error closing audio context:', error);
            }
        }
        
        console.log('Audio visualizer cleanup complete');
    }
}

export { AudioVisualizer };
