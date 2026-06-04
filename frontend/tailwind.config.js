/** @type {import('tailwindcss').Config} */
export default {
    content: [
        "./index.html",
        "./src/**/*.{js,ts,jsx,tsx}",
    ],
    theme: {
        extend: {
            colors: {
                gray: {
                    50: '#fafafa',
                    100: '#f4f4f5',
                    200: '#e4e4e7',
                    300: '#d4d4d8',
                    400: '#a1a1aa',
                    500: '#71717a',
                    600: '#52525b',
                    700: '#3f3f46',
                    750: '#34343a',
                    800: '#27272a',
                    850: '#1f1f23',
                    900: '#18181b',
                    950: '#0a0a0b',
                },
                primary: {
                    50: '#f5f7f2',
                    100: '#e6eadf',
                    200: '#ced8bf',
                    300: '#afbf96',
                    400: '#879d6a',
                    500: '#667b4f',
                    600: '#4f6040',
                    700: '#3f4d34',
                    800: '#323d2b',
                    900: '#283124',
                }
            },
            fontFamily: {
                sans: ['Inter', 'system-ui', 'sans-serif'],
            },
            boxShadow: {
                'glass': '0 4px 30px rgba(0, 0, 0, 0.1)',
                'glow': '0 0 15px rgba(102, 123, 79, 0.28)',
            },
            backdropBlur: {
                'xs': '2px',
            }
        },
    },
    plugins: [],
}
