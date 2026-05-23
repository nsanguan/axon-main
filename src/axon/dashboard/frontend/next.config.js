/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  rewrites: async () => [
    {
      source: '/api/:path*',
      destination: 'http://axon-api:8020/api/:path*',
    },
  ],
}

module.exports = nextConfig
