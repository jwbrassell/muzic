class CirclesVisualizer extends BaseVisualizer {
    constructor(canvas, analyser) {
        super(canvas, analyser);
        this.color1 = this.getRandomColor();
        this.color2 = this.getRandomColor();
    }

    draw() {
        this.analyser.getByteFrequencyData(this.dataArray);
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        const centerX = width / 2;
        const centerY = height / 2;
        
        this.canvasCtx.clearRect(0, 0, width, height);
        
        const gradient = this.getGradient(this.color1, this.color2);
        this.canvasCtx.fillStyle = gradient;
        
        for (let i = 0; i < this.dataArray.length; i++) {
            const value = this.dataArray[i];
            const radius = (value / 255) * Math.min(width, height) / 3;
            const angle = (i / this.dataArray.length) * Math.PI * 2;
            
            const x = centerX + Math.cos(angle) * radius;
            const y = centerY + Math.sin(angle) * radius;
            
            this.canvasCtx.beginPath();
            this.canvasCtx.arc(x, y, 4, 0, Math.PI * 2);
            this.canvasCtx.fill();
        }
    }
}
