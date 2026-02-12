/** @type {import('tailwindcss').Config} */
module.exports = {
  content: [
    "./templates/**/*.html",
    "./**/templates/**/*.html",
    "./attendance/**/*.html",
    "./patients/**/*.html",
    "./core/**/*.html",
    "./**/*.py",
  ],
  theme: {
    extend: {},
  },
  plugins: [],
};
