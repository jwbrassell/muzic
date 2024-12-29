import { BaseVisualizer } from './base.js';

export class CirclesVisualizer extends BaseVisualizer {
    constructor(canvas, analyser) {
        super(canvas, analyser);
        const colors = this.getThemeColors();
        this.color1 = colors.primary;
        this.color2 = colors.secondary;
    }

    draw() {
        this.analyser.getByteFrequencyData(this.dataArray);
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;
        
        this.canvasCtx.clearRect(0, 0, width, height);
        
        // Set up intense glow effect for circles
        this.canvasCtx.shadowBlur = 20;
        this.canvasCtx.shadowColor = this.getThemeColors().primary;
        
        const gradient = this.getGradient(this.color1, this.color2);
        this.canvasCtx.fillStyle = gradient;
        
        for (let i = 0; i < this.dataArray.length; i++) {
            const value = this.dataArray[i];
            // Increase the radius range to use more space
            const radius = (value / 255) * Math.min(width, height) / 2;
            const angle = (i / this.dataArray.length) * Math.PI * 2;
            
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            
            // Larger circle sizes
            const circleSize = Math.max(3, (value / 255) * 8);
            
            this.canvasCtx.beginPath();
            this.canvasCtx.arc(x, y, circleSize, 0, Math.PI * 2);
            this.canvasCtx.fill();
        }
        
        // Reset shadow
        this.canvasCtx.shadowBlur = 0;
    }
}
