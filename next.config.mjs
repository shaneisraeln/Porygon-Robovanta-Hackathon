import path from "node:path";

/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  // Pin the workspace root to this project (a lockfile exists higher up).
  turbopack: {
    root: path.resolve("."),
  },
};

export default nextConfig;
