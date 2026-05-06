/** @type {import('tailwindcss').Config} */
export default {
  content: ["./src/**/*.{html,js}"],
  theme: {
    extend: {
      colors: {
        surface: {
          bg: "#0f1923",
          card: "#1a2332",
          border: "#2a3a4a",
        },
        status: {
          ok: "#6ee7b7",
          warn: "#fbbf24",
          error: "#f87171",
          pending: "#93c5fd",
        },
      },
    },
  },
};
