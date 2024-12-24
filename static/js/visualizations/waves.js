class WavesVisualizer extends BaseVisualizer {
    constructor(canvas, analyser) {
        super(canvas, analyser);
        this.color1 = this.getRandomColor();
        this.color2 = this.getRandomColor();
    }

    draw() {
        this.analyser.getByteFrequencyData(this.dataArray);
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        this.canvasCtx.clearRect(0, 0, width, height);
        
        const gradient = this.getGradient(this.color1, this.color2);
        this.canvasCtx.strokeStyle = gradient;
        this.canvasCtx.lineWidth = 2;
        
        this.canvasCtx.beginPath();
        this.canvasCtx.moveTo(0, height / 2);
        
        for (let i = 0; i < this.dataArray.length; i++) {
            const value = this.dataArray[i];
            const percent = value / 255;
            const x = width * (i / this.dataArray.length);
            const y = height / 2 + (height / 2 * percent * Math.sin(i * 0.1));
            
            if (i === 0) {
                this.canvasCtx.moveTo(x, y);
            } else {
                this.canvasCtx.lineTo(x, y);
            }
        }
        
        this.canvasCtx.stroke();
        
        // Mirror the wave
        this.canvasCtx.beginPath();
        for (let i = 0; i < this.dataArray.length; i++) {
            const value = this.dataArray[i];
            const percent = value / 255;
            const x = width * (i / this.dataArray.length);
            const y = height / 2 - (height / 2 * percent * Math.sin(i * 0.1));
            
            if (i === 0) {
                this.canvasCtx.moveTo(x, y);
            } else {
                this.canvasCtx.lineTo(x, y);
            }
        }
        this.canvasCtx.stroke();
    }
}
