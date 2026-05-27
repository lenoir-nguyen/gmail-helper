import type { NextConfig } from "next";
import path from "path";

const nextConfig: NextConfig = {
  images: {
    remotePatterns: [
      {
        protocol: "https",
        hostname: "lh3.googleusercontent.com", // Google profile pictures
      },
    ],
  },
  turbopack: {
    root: path.resolve(__dirname), // Pin workspace root to this folder
  },
};

export default nextConfig;
