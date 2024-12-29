import { BaseVisualizer } from './base.js';

export class BarsVisualizer extends BaseVisualizer {
    constructor(canvas, analyser) {
        super(canvas, analyser);
        const colors = this.getThemeColors();
        this.color1 = colors.primary;
        this.color2 = colors.accent;
    }

    draw() {
        this.analyser.getByteFrequencyData(this.dataArray);
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        // Use more horizontal space while maintaining proper spacing
        const scaleFactor = 2.5;
        const barWidth = (width / this.dataArray.length) * scaleFactor;
        
        // Center the visualization
        const totalVisualizerWidth = barWidth * this.dataArray.length;
        const startX = (width - totalVisualizerWidth) / 2;
        
        // Scale factor for height to use more vertical space
        const heightScale = 1.2;
        
        this.canvasCtx.clearRect(0, 0, width, height);
        
        const gradient = this.getGradient(this.color1, this.color2);
        
        this.dataArray.forEach((value, index) => {
            const barHeight = (value / 255) * height * heightScale;
            const x = startX + (index * barWidth);
            const y = height - barHeight;
            
            // Add glow effect
            this.canvasCtx.shadowBlur = 15;
            this.canvasCtx.shadowColor = this.getThemeColors().glow;
            
            this.canvasCtx.fillStyle = gradient;
            this.canvasCtx.fillRect(x, y, barWidth - 2, barHeight);
            
            // Reset shadow for next iteration
            this.canvasCtx.shadowBlur = 0;
        });
    }
}
