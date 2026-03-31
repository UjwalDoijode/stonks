/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        profit: "#00ff41",
        loss: "#ff3232",
        accent: "#cfb57e",
        "accent-2": "#a68a55",
        "accent-light": "#e8d5a8",
        surface: "#0a0e1a",
        "surface-2": "#10162a",
        "surface-3": "#161d35",
        base: "#04060e",
        border: "rgba(207, 181, 126, 0.12)",
        muted: "#5a6478",
        cyan: "#00d4ff",
        amber: "#cfb57e",
        matrix: "#00ff41",
        "matrix-dim": "#00cc33",
        gold: "#cfb57e",
        "gold-bright": "#e8d5a8",
        "gold-dark": "#a68a55",
        danger: "#ff3232",
        warning: "#ff9500",
      },
      fontFamily: {
        sans: ['"Space Grotesk"', '"Outfit"', 'system-ui', 'sans-serif'],
        mono: ['"IBM Plex Mono"', '"Fira Code"', 'monospace'],
        display: ['"Outfit"', '"Space Grotesk"', 'sans-serif'],
      },
      boxShadow: {
        glow: "0 0 20px rgba(207, 181, 126, 0.15)",
        "glow-gold": "0 0 24px rgba(207, 181, 126, 0.2)",
        "glow-green": "0 0 20px rgba(0, 255, 65, 0.15)",
        "glow-red": "0 0 20px rgba(255, 50, 50, 0.15)",
        card: "0 2px 8px rgba(0,0,0,0.5), 0 0 0 1px rgba(207,181,126,0.08)",
        "card-hover": "0 8px 32px rgba(0,0,0,0.6), 0 0 0 1px rgba(207,181,126,0.2)",
        terminal: "0 0 30px rgba(0, 255, 65, 0.05), inset 0 1px 0 rgba(0, 255, 65, 0.03)",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "card-gradient": "linear-gradient(145deg, rgba(10,14,26,0.95), rgba(16,22,40,0.75))",
        "header-gradient": "linear-gradient(90deg, rgba(207,181,126,0.06), transparent)",
        "gold-gradient": "linear-gradient(135deg, #cfb57e, #e8d5a8, #a68a55)",
        "matrix-gradient": "linear-gradient(180deg, rgba(0,255,65,0.05), transparent)",
      },
      animation: {
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "fade-in": "fadeIn 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
        "slide-up": "slideUp 0.4s cubic-bezier(0.4, 0, 0.2, 1)",
        shimmer: "shimmer 2.5s linear infinite",
        "glow-pulse": "glowPulse 3s ease-in-out infinite",
        "terminal-flicker": "terminalFlicker 4s ease-in-out infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(12px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        glowPulse: {
          "0%, 100%": { opacity: "0.6" },
          "50%": { opacity: "1" },
        },
        terminalFlicker: {
          "0%, 100%": { opacity: "1" },
          "50%": { opacity: "0.97" },
          "51%": { opacity: "1" },
        },
      },
    },
  },
  plugins: [],
};
