/** @type {import('tailwindcss').Config} */
export default {
  content: ["./index.html", "./src/**/*.{ts,tsx}"],
  theme: {
    extend: {
      colors: {
        // SAP Fiori-inspired, but our own palette
        brand: {
          50: "#eef4fb", 100: "#d6e5f5", 200: "#aecbea", 300: "#7aa9da",
          500: "#1c6fc9", 600: "#0a5aad", 700: "#084a8f", 800: "#073c73", 900: "#06305c",
        },
        shell: { bg: "#0a1929", header: "#0a2540", sidebar: "#102a43", panel: "#ffffff" },
        status: { ok: "#2e7d32", warn: "#ed6c02", high: "#d32f2f", crit: "#7b1fa2", info: "#0277bd" },
      },
      fontFamily: {
        sans: ["'72'", "Inter", "system-ui", "Arial", "sans-serif"],
        mono: ["'JetBrains Mono'", "ui-monospace", "SFMono-Regular", "monospace"],
      },
      boxShadow: { card: "0 1px 3px rgba(0,0,0,0.08), 0 1px 2px rgba(0,0,0,0.06)" },
    },
  },
  plugins: [],
};
