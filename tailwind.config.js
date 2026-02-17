/** @type {import('tailwindcss').Config} */
export default {
  content: [
    "./index.html",
    "./frontend/src/**/*.{js,jsx}",
  ],
  theme: {
    extend: {
      colors: {
        campfire: {
          50: '#fef7ee',
          100: '#fdedd3',
          200: '#fad7a5',
          300: '#f6ba6d',
          400: '#f19333',
          500: '#ee7a12',
          600: '#df6008',
          700: '#b94809',
          800: '#93390e',
          900: '#77310f',
          950: '#401605',
        },
        forest: {
          50: '#f0fdf0',
          100: '#dcfcdc',
          200: '#bbf7bc',
          300: '#86ef89',
          400: '#4ade50',
          500: '#22c528',
          600: '#16a31c',
          700: '#158019',
          800: '#166519',
          900: '#145317',
          950: '#052e09',
        },
      },
    },
  },
  plugins: [],
};
