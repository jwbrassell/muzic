export class BaseVisualizer {
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

    getThemeColors() {
        // Brand theme colors with consideration for visibility in both modes
        return {
            primary: '#FF1A1A',     // Bright red like the logo
            secondary: '#FF0000',    // Pure red for contrast
            accent: '#800000',       // Darker red for depth
            glow: 'rgba(255, 0, 0, 0.3)', // Red glow effect
            dark: '#1A1A1A',         // Near black for dark mode
            light: '#FFFFFF'         // White for light mode contrast
        };
    }

    getRandomThemeColor() {
        const colors = this.getThemeColors();
        const themeColors = [colors.primary, colors.secondary, colors.accent];
        return themeColors[Math.floor(Math.random() * themeColors.length)];
    }

    getGradient(startColor, endColor) {
        const colors = this.getThemeColors();
        const gradient = this.canvasCtx.createLinearGradient(0, this.canvas.height, 0, 0);
        
        // Add glow effect
        gradient.addColorStop(0, colors.glow);
        gradient.addColorStop(0.2, startColor);
        gradient.addColorStop(0.8, endColor);
        gradient.addColorStop(1, colors.glow);
        
        return gradient;
    }
}
