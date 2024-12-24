class BaseVisualizer {
    constructor(canvas, analyser) {
        this.canvas = canvas;
        this.canvasCtx = canvas.getContext('2d');
        this.analyser = analyser;
        this.dataArray = new Uint8Array(analyser.frequencyBinCount);
    }

    draw() {
        // To be implemented by child classes
        throw new Error('Draw method must be implemented');
    }

    getRandomColor() {
        const colors = [
            '#FF0000', '#00FF00', '#0000FF', 
            '#FFFF00', '#FF00FF', '#00FFFF',
            '#FFA500', '#800080', '#FFC0CB',
            '#40E0D0', '#FF69B4', '#7CFC00'
        ];
        return colors[Math.floor(Math.random() * colors.length)];
    }

    getGradient(startColor, endColor) {
        const gradient = this.canvasCtx.createLinearGradient(0, this.canvas.height, 0, 0);
        gradient.addColorStop(0, startColor);
        gradient.addColorStop(1, endColor);
        return gradient;
    }
}
