/** @type {import('next').NextConfig} */
const nextConfig = {
  // Removed output:'export' to allow dynamic routes (admin user detail pages)
  distDir: '.next',
  images: { unoptimized: true },
};

module.exports = nextConfig;
