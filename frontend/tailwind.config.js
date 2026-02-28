/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        profit: "#10b981",
        loss: "#ef4444",
        accent: "#3b82f6",
        "accent-2": "#8b5cf6",
        surface: "#111827",
        "surface-2": "#1f2937",
        base: "#030712",
        border: "#1e293b",
        muted: "#64748b",
        cyan: "#06b6d4",
        amber: "#f59e0b",
      },
      fontFamily: {
        sans: ['"Inter"', '"SF Pro Display"', 'system-ui', 'sans-serif'],
        mono: ['"JetBrains Mono"', '"Fira Code"', 'monospace'],
      },
      boxShadow: {
        glow: "0 0 20px rgba(59, 130, 246, 0.15)",
        "glow-green": "0 0 20px rgba(16, 185, 129, 0.15)",
        "glow-red": "0 0 20px rgba(239, 68, 68, 0.15)",
        card: "0 1px 3px rgba(0,0,0,0.4), 0 0 0 1px rgba(30,41,59,0.5)",
        "card-hover": "0 4px 12px rgba(0,0,0,0.5), 0 0 0 1px rgba(59,130,246,0.3)",
      },
      backgroundImage: {
        "gradient-radial": "radial-gradient(var(--tw-gradient-stops))",
        "card-gradient": "linear-gradient(135deg, rgba(17,24,39,0.9), rgba(31,41,55,0.6))",
        "header-gradient": "linear-gradient(90deg, rgba(59,130,246,0.08), transparent)",
      },
      animation: {
        "pulse-slow": "pulse 3s ease-in-out infinite",
        "fade-in": "fadeIn 0.3s ease-out",
        "slide-up": "slideUp 0.3s ease-out",
        shimmer: "shimmer 2s linear infinite",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        slideUp: {
          "0%": { opacity: "0", transform: "translateY(10px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
      },
    },
  },
  plugins: [],
};
