/** @type {import('tailwindcss').Config} */
module.exports = {
  content: ["./templates/**/*.html", "./templates/**/*.css"],
  theme: {
    extend: {
      fontFamily: {
        mono: [
          "ui-monospace",
          "SFMono-Regular",
          "SF Mono",
          "Menlo",
          "Consolas",
          "Liberation Mono",
          "monospace",
        ],
      },
    },
  },
  plugins: [],
};
