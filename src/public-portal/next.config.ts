import type { NextConfig } from "next";
import path from "node:path";

const nextConfig: NextConfig = {
  output: "standalone",
  turbopack: {
    root: path.resolve(__dirname, ".."),
  },
  experimental: {
    // Resumes up to 5 MB are posted through a Server Action; the default limit is 1 MB.
    serverActions: { bodySizeLimit: "6mb" },
  },
};

export default nextConfig;
