/** @type {import('next').NextConfig} */
const nextConfig = {
  output: 'standalone',
  // REMOVED rewrites to avoid conflicts - frontend will call backend directly via fetch
  // async rewrites() {
  //   const apiBase = process.env.NEXT_PUBLIC_API_URL;
  //   if (!apiBase) return [];
  //   return [
  //     {
  //       source: '/api/:path*',
  //       destination: `${apiBase}/:path*`,
  //     },
  //   ];
  // },
};

module.exports = nextConfig;


