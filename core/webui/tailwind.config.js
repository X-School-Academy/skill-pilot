/** @type {import('tailwindcss').Config} */
const colors = require('tailwindcss/colors')
const defaultConfig = require('tailwindcss/defaultConfig')
module.exports = {
  content: [
    "./pages/**/*.{js,ts,jsx,tsx}",
    "./components/**/*.{js,ts,jsx,tsx}",
  ],
  theme: {
    extend: {
      typography: {
        DEFAULT: {
          css: {
            color: 'rgb(17,24,39)',
          },
        },
      },
      backgroundImage: {
        'login-bg': 'url(/img/login.jpg)'
      },
      fontSize: {
        'xxxs': '0.125rem',
        'xxs': '0.625rem'
      },
      width: {
        '118': '30rem',
        '128': '32rem',
      },
      height: {
        '118': '30rem',
        '128': '32rem',
      },
      top: {
        'n1': '-10rem'
      }
    },
    colors: {
      'side-menu-bg-color': '#EEEFFE',
      'side-menu-selected-bg-color': '#DFE1FD',
      white: {
        DEFAULT: '#FFFFFF'
      },
      'blue-dark': '#373c93',
      'red': '#E73422',
      'primary-blue': '#373c93',
      'primary-dark-blue': '#373c93',
      'primary-bg-color': '#F9FAFC',
      'secondary-orange': '#FE7163',
      'secondary-blue': '#373c93',
      'secondary-purple': '#D269CB',
      'secondary-green': '#00a67d',
      'secondary-yellow': '#F7DF1E',
      'secondary-bg': '#F0F1FF',
      'creative-primary-color': '#D7153A',
      'creative-secondary-color': '#4ECB71',
      'creative-orange': '#F2994A',
      'creative-purple': '#9B51E0',
      'discord-black': '#000000',
      'discord-blue': '#0057FF',
      'live-class-black-gray': '#27283D',
      'live-class-yellow':'#EBE932',
      'live-class-orange': '#FDA24F',
      gray: colors.gray,
      blue: colors.blue,
      green: colors.green,

    },
    screens: {
      'sm': '640px',
      'md': '768px',
      'lg': '1024px',
      'xl': '1280px',
      '2xl': '1536px',
      "3xl": '3000px',
      'jit-xl': '1440px'
    }
  },
  plugins: [
    require('@tailwindcss/typography'),
    require('@tailwindcss/forms'),
  ],
}
