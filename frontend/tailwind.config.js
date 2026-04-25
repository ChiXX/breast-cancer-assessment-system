/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./src/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: "hsl(220, 90%, 56%)",
        background: "hsl(210, 20%, 98%)",
        high: "hsl(0, 84%, 60%)",
        medium: "hsl(35, 92%, 50%)",
        low: "hsl(142, 71%, 45%)",
      },
      borderRadius: {
        'xl': '12px',
        '2xl': '16px',
      }
    },
  },
  plugins: [],
}
