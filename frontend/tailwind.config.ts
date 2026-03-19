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
          DEFAULT: "rgb(var(--color-primary) / <alpha-value>)",
          hover: "rgb(var(--color-primary-hover) / <alpha-value>)",
          light: "rgb(var(--color-primary-light) / <alpha-value>)",
        },
        surface: "rgb(var(--color-surface) / <alpha-value>)",
        muted: {
          DEFAULT: "rgb(var(--color-muted) / <alpha-value>)",
          light: "rgb(var(--color-muted-light) / <alpha-value>)",
        },
        border: "rgb(var(--color-border) / <alpha-value>)",
        "border-light": "rgb(var(--color-border-light) / <alpha-value>)",
        success: {
          DEFAULT: "rgb(var(--color-success) / <alpha-value>)",
          light: "rgb(var(--color-success-light) / <alpha-value>)",
        },
        warning: {
          DEFAULT: "rgb(var(--color-warning) / <alpha-value>)",
          light: "rgb(var(--color-warning-light) / <alpha-value>)",
        },
        danger: {
          DEFAULT: "rgb(var(--color-danger) / <alpha-value>)",
          light: "rgb(var(--color-danger-light) / <alpha-value>)",
        },
        info: {
          DEFAULT: "rgb(var(--color-info) / <alpha-value>)",
          light: "rgb(var(--color-info-light) / <alpha-value>)",
        },
      },
      borderRadius: {
        sm: "var(--radius-sm)",
        md: "var(--radius-md)",
        lg: "var(--radius-lg)",
        xl: "var(--radius-xl)",
      },
      boxShadow: {
        xs: "var(--shadow-xs)",
        sm: "var(--shadow-sm)",
        md: "var(--shadow-md)",
        lg: "var(--shadow-lg)",
        xl: "var(--shadow-xl)",
      },
      fontSize: {
        xs: ["var(--font-xs)", { lineHeight: "1.5" }],
        sm: ["var(--font-sm)", { lineHeight: "1.5" }],
        base: ["var(--font-base)", { lineHeight: "1.6" }],
        md: ["var(--font-md)", { lineHeight: "1.5" }],
        lg: ["var(--font-lg)", { lineHeight: "1.4" }],
        xl: ["var(--font-xl)", { lineHeight: "1.3" }],
        "2xl": ["var(--font-2xl)", { lineHeight: "1.2" }],
        "3xl": ["var(--font-3xl)", { lineHeight: "1.2" }],
      },
      spacing: {
        sidebar: "var(--sidebar-width)",
        "sidebar-collapsed": "var(--sidebar-collapsed-width)",
      },
    },
  },
  plugins: [],
};
export default config;
