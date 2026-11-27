/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return {
      // Serve the static home page at the root domain.
      beforeFiles: [{ source: "/", destination: "/index.html" }],
    };
  },
};

module.exports = nextConfig;
