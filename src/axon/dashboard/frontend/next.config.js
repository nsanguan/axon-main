/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  rewrites: async () => [
    {
      source: '/api/:path*',
      destination: 'http://localhost:8200/api/:path*',
    },
  ],
}

module.exports = nextConfig
