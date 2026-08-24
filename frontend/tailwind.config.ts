/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{js,ts,jsx,tsx}'],
  theme: {
    extend: {
      colors: {
        razorpay: {
          blue: '#3395FF',
          navy: '#0C2451',
          lightblue: '#EBF4FF',
        },
        status: {
          recovered: '#22C55E',
          inprogress: '#F59E0B',
          escalated: '#EF4444',
          writtenoff: '#64748B',
          humanpending: '#8B5CF6',
          open: '#94A3B8',
        },
      },
      fontFamily: {
        sans: ['Inter', 'sans-serif'],
        mono: ['JetBrains Mono', 'monospace'],
      },
    },
  },
  plugins: [],
}
