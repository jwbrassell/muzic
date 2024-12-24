class BarsVisualizer extends BaseVisualizer {
    constructor(canvas, analyser) {
        super(canvas, analyser);
        this.color1 = this.getRandomColor();
        this.color2 = this.getRandomColor();
    }

    draw() {
        this.analyser.getByteFrequencyData(this.dataArray);
        
        const width = this.canvas.width;
        const height = this.canvas.height;
        
        // Scale up the bars to use more space while maintaining spacing
        const scaleFactor = 1.5; // Makes bars wider but not too wide
        const barWidth = (width / this.dataArray.length) * scaleFactor;
        
        // Center the visualization
        const totalVisualizerWidth = barWidth * this.dataArray.length;
        const startX = (width - totalVisualizerWidth) / 2;
        
        this.canvasCtx.clearRect(0, 0, width, height);
        
        const gradient = this.getGradient(this.color1, this.color2);
        
        this.dataArray.forEach((value, index) => {
            const barHeight = (value / 255) * height;
            const x = startX + (index * barWidth);
            const y = height - barHeight;
            
            this.canvasCtx.fillStyle = gradient;
            this.canvasCtx.fillRect(x, y, barWidth - 2, barHeight); // Increased gap between bars
        });
    }
}
