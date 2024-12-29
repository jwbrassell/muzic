import { BaseVisualizer } from './base.js';

export class FaceVisualizer extends BaseVisualizer {
    constructor(canvas, analyser) {
        super(canvas, analyser);
        
        // Center coordinates for facial features
        this.centerX = this.canvas.width / 2;
        this.centerY = this.canvas.height / 2;
        
        // Base sizes for facial features
        this.eyeRadius = 30;
        this.noseSize = 20;
        this.mouthWidth = 100;
        this.mouthHeight = 30;
    }

    draw() {
        // Get audio data
        this.analyser.getByteFrequencyData(this.dataArray);
        
        // Clear canvas
        this.canvasCtx.clearRect(0, 0, this.canvas.width, this.canvas.height);
        
        // Calculate average frequencies for different ranges
        const bassAvg = this.getAverageFrequency(0, 10);    // Bass (eyes)
        const midAvg = this.getAverageFrequency(11, 100);   // Mids (mouth)
        const highAvg = this.getAverageFrequency(101, 200); // Highs (nose)
        
        const colors = this.getThemeColors();
        this.canvasCtx.strokeStyle = colors.primary;
        this.canvasCtx.fillStyle = colors.primary;
        this.canvasCtx.lineWidth = 2;
        
        // Draw eyes that pulse with bass
        const eyeScale = 1 + (bassAvg / 255) * 0.5;
        this.drawEye(-80, -20, eyeScale); // Left eye
        this.drawEye(80, -20, eyeScale);  // Right eye
        
        // Draw nose that changes with high frequencies
        const noseScale = 1 + (highAvg / 255) * 0.3;
        this.drawNose(noseScale);
        
        // Draw mouth that moves with mid frequencies
        const mouthScale = 1 + (midAvg / 255) * 0.5;
        this.drawMouth(mouthScale);
    }
    
    drawEye(offsetX, offsetY, scale) {
        const x = this.centerX + offsetX;
        const y = this.centerY + offsetY;
        
        // Add glow effect
        this.canvasCtx.shadowBlur = 15;
        this.canvasCtx.shadowColor = this.getThemeColors().glow;
        
        // Draw eye outline
        this.canvasCtx.beginPath();
        this.canvasCtx.arc(x, y, this.eyeRadius * scale, 0, Math.PI * 2);
        this.canvasCtx.stroke();
        
        // Add pupil
        this.canvasCtx.beginPath();
        this.canvasCtx.arc(x, y, this.eyeRadius * scale * 0.4, 0, Math.PI * 2);
        this.canvasCtx.fill();
        
        // Reset shadow
        this.canvasCtx.shadowBlur = 0;
    }
    
    drawNose(scale) {
        const size = this.noseSize * scale;
        
        // Add glow effect
        this.canvasCtx.shadowBlur = 15;
        this.canvasCtx.shadowColor = this.getThemeColors().glow;
        
        this.canvasCtx.beginPath();
        this.canvasCtx.moveTo(this.centerX, this.centerY - size/2);
        this.canvasCtx.lineTo(this.centerX - size/2, this.centerY + size/2);
        this.canvasCtx.lineTo(this.centerX + size/2, this.centerY + size/2);
        this.canvasCtx.closePath();
        this.canvasCtx.stroke();
        
        // Reset shadow
        this.canvasCtx.shadowBlur = 0;
    }
    
    drawMouth(scale) {
        const width = this.mouthWidth * scale;
        const height = this.mouthHeight * scale;
        
        // Add glow effect
        this.canvasCtx.shadowBlur = 15;
        this.canvasCtx.shadowColor = this.getThemeColors().glow;
        
        this.canvasCtx.beginPath();
        this.canvasCtx.ellipse(
            this.centerX,
            this.centerY + 50,
            width/2,
            height/2,
            0,
            0,
            Math.PI
        );
        this.canvasCtx.stroke();
        
        // Reset shadow
        this.canvasCtx.shadowBlur = 0;
    }
    
    getAverageFrequency(start, end) {
        let sum = 0;
        for (let i = start; i < end; i++) {
            sum += this.dataArray[i];
        }
        return sum / (end - start);
    }
}
