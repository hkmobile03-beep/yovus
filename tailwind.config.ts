import type { Config } from "tailwindcss";

const config: Config = {
  content: [
    "./src/pages/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/components/**/*.{js,ts,jsx,tsx,mdx}",
    "./src/app/**/*.{js,ts,jsx,tsx,mdx}",
  ],
  theme: {
    extend: {
      colors: {
        primary: {
          DEFAULT: "#3F8FFE",
          dark: "#2B7AE8",
          light: "#6AADFF",
        },
        secondary: "#50493F",
        cream: {
          DEFAULT: "#E5E6E0",
          light: "#FAFAF8",
          dark: "#D5D6D0",
        },
        warm: {
          DEFAULT: "#FFE8D6",
          light: "#FFF5ED",
          dark: "#FFD4B3",
        },
        section: "#F5F5F0",
      },
      fontFamily: {
        sans: [
          '"Noto Sans JP"',
          '"Noto Sans SC"',
          "system-ui",
          "-apple-system",
          "sans-serif",
        ],
      },
      borderRadius: {
        soft: "12px",
        card: "16px",
        button: "9999px",
      },
      animation: {
        "fade-in": "fadeIn 0.6s ease-out forwards",
        "fade-up": "fadeUp 0.6s ease-out forwards",
        "slide-in-left": "slideInLeft 0.6s ease-out forwards",
        "slide-in-right": "slideInRight 0.6s ease-out forwards",
        float: "float 3s ease-in-out infinite",
        "cart-bounce": "cartBounce 0.4s ease-out",
      },
      keyframes: {
        fadeIn: {
          "0%": { opacity: "0" },
          "100%": { opacity: "1" },
        },
        fadeUp: {
          "0%": { opacity: "0", transform: "translateY(30px)" },
          "100%": { opacity: "1", transform: "translateY(0)" },
        },
        slideInLeft: {
          "0%": { opacity: "0", transform: "translateX(-30px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        slideInRight: {
          "0%": { opacity: "0", transform: "translateX(30px)" },
          "100%": { opacity: "1", transform: "translateX(0)" },
        },
        float: {
          "0%, 100%": { transform: "translateY(0)" },
          "50%": { transform: "translateY(-10px)" },
        },
        cartBounce: {
          "0%": { transform: "scale(1)" },
          "50%": { transform: "scale(1.2)" },
          "100%": { transform: "scale(1)" },
        },
      },
    },
  },
  plugins: [],
};
export default config;
