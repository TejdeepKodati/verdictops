/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{js,ts,jsx,tsx}"],
  theme: {
    extend: {
      colors: {
        canvas: "#FAF7F2",
        surface: "#FFFFFF",
        inset: "#F1ECE3",
        ink: "#1B1424",
        muted: "#5E5468",
        rule: "#DDD5C7",
        burgundy: "#9F1239",
        forest: "#047857",
        ochre: "#B45309",
        "ochre-text": "#92400E",
        crimson: "#B91C1C",
      },
      fontFamily: {
        serif: ['"Bitter"', "Georgia", "serif"],
        sans: ['"Public Sans"', "system-ui", "-apple-system", "sans-serif"],
        mono: ['"JetBrains Mono"', "ui-monospace", "SFMono-Regular", "monospace"],
      },
    },
  },
  plugins: [],
};
