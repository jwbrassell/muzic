import { BaseVisualizer } from './base.js';

export class WavesVisualizer extends BaseVisualizer {
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
        
        this.canvasCtx.clearRect(0, 0, width, height);
        
        // Set up neon glow effect
        this.canvasCtx.shadowBlur = 15;
        this.canvasCtx.shadowColor = this.getThemeColors().primary;
        
        const gradient = this.getGradient(this.color1, this.color2);
        this.canvasCtx.strokeStyle = gradient;
        this.canvasCtx.lineWidth = 4; // Thicker lines for better visibility
        
        // Draw upper wave
        this.canvasCtx.beginPath();
        this.canvasCtx.moveTo(0, height / 2);
        
        for (let i = 0; i < this.dataArray.length; i++) {
            const value = this.dataArray[i];
            const percent = value / 255;
            const x = width * (i / this.dataArray.length);
            // Use more vertical space and create wider wave patterns
            const y = height / 2 + (height * 0.4 * percent * Math.sin(i * 0.05));
            
            if (i === 0) {
                this.canvasCtx.moveTo(x, y);
            } else {
                this.canvasCtx.lineTo(x, y);
            }
        }
        
        this.canvasCtx.stroke();
        
        // Draw lower wave with different color
        this.canvasCtx.strokeStyle = this.getGradient(this.color2, this.color1); // Reverse gradient
        this.canvasCtx.beginPath();
        
        for (let i = 0; i < this.dataArray.length; i++) {
            const value = this.dataArray[i];
            const percent = value / 255;
            const x = width * (i / this.dataArray.length);
            // Mirror wave with same wider pattern
            const y = height / 2 - (height * 0.4 * percent * Math.sin(i * 0.05));
            
            if (i === 0) {
                this.canvasCtx.moveTo(x, y);
            } else {
                this.canvasCtx.lineTo(x, y);
            }
        }
        
        this.canvasCtx.stroke();
        
        // Reset shadow
        this.canvasCtx.shadowBlur = 0;
    }
}
