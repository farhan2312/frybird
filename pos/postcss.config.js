import oldWebview from './postcss-old-webview.js'

export default {
  plugins: [
    (await import('tailwindcss')).default(),
    oldWebview(),
    (await import('autoprefixer')).default(),
  ],
}
