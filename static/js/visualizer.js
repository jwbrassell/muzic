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
        this.visualizerTypes = [BarsVisualizer, CirclesVisualizer, WavesVisualizer];
        this.initializationPromise = null;
        
        // Add resize listener once during construction
        window.addEventListener('resize', () => this.resizeCanvas());
    }

    async initialize(audioElement) {
        // If already initializing, wait for that to complete
        if (this.initializationPromise) {
            return this.initializationPromise;
        }

        // Create new initialization promise
        this.initializationPromise = (async () => {
            try {
                // Only create new context if none exists or if closed
                if (!this.audioContext || this.audioContext.state === 'closed') {
                    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    this.analyser = this.audioContext.createAnalyser();
                    this.source = this.audioContext.createMediaElementSource(audioElement);
                    this.source.connect(this.analyser);
                    this.analyser.connect(this.audioContext.destination);
                } else if (this.audioContext.state === 'suspended') {
                    // Resume existing context if suspended
                    await this.audioContext.resume();
                }

                // Set up analyzer configuration
                this.analyser.fftSize = 256;
                const bufferLength = this.analyser.frequencyBinCount;
                this.dataArray = new Uint8Array(bufferLength);
                
                // Set canvas size
                this.resizeCanvas();
                
                // Initialize with random visualizer if none exists
                if (!this.currentVisualizer) {
                    this.switchVisualizer();
                }
                
                this.isInitialized = true;
                
                // Start drawing if not already
                if (!this.animationId) {
                    this.draw();
                }
            } catch (error) {
                console.error('Error initializing audio context:', error);
                this.isInitialized = false;
                // Try to recover by closing and recreating context
                try {
                    if (this.audioContext) {
                        await this.audioContext.close();
                    }
                    this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
                    this.analyser = this.audioContext.createAnalyser();
                    this.source = this.audioContext.createMediaElementSource(audioElement);
                    this.source.connect(this.analyser);
                    this.analyser.connect(this.audioContext.destination);
                    this.isInitialized = true;
                } catch (retryError) {
                    console.error('Failed to recover audio context:', retryError);
                    throw retryError;
                }
            } finally {
                this.initializationPromise = null;
            }
        })();

        return this.initializationPromise;
    }

    resizeCanvas() {
        // Get the container's dimensions
        const container = this.canvas.parentElement;
        this.canvas.width = container.offsetWidth;
        this.canvas.height = container.offsetHeight;
    }

    switchVisualizer() {
        const VisualizerType = this.visualizerTypes[Math.floor(Math.random() * this.visualizerTypes.length)];
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
        // Don't reset initialization state - we might want to resume
    }

    async cleanup() {
        this.stop();
        if (this.audioContext) {
            try {
                await this.audioContext.close();
                this.audioContext = null;
                this.analyser = null;
                this.source = null;
                this.isInitialized = false;
            } catch (error) {
                console.error('Error cleaning up audio context:', error);
            }
        }
    }
}
