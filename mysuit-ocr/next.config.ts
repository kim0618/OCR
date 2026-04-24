import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  devIndicators: false,
  async rewrites() {
    const backendUrl = process.env.BACKEND_URL || "http://localhost:8000";

    return [
      { source: "/api/:path*",        destination: `${backendUrl}/:path*` },
      { source: "/login/:path*",      destination: `${backendUrl}/login/:path*` },
      { source: "/admin/:path*",      destination: `${backendUrl}/admin/:path*` },
      { source: "/main/:path*",       destination: `${backendUrl}/main/:path*` },
      { source: "/ocr/:path*",        destination: `${backendUrl}/ocr/:path*` },
      { source: "/preprocess/:path*", destination: `${backendUrl}/preprocess/:path*` },
      { source: "/templates/:path*",  destination: `${backendUrl}/templates/:path*` },
      { source: "/templates",         destination: `${backendUrl}/templates` },
      { source: "/health",            destination: `${backendUrl}/health` },
    ];
  },
  webpack: (config: any, { isServer }: any) => {
    config.resolve = config.resolve || {};
    // pdfjs-dist가 Node 전용 canvas 모듈을 require 하지 않도록 차단
    config.resolve.alias = {
      ...(config.resolve.alias || {}),
      canvas: false,
    };

    if (!isServer) {
      config.resolve.fallback = {
        ...(config.resolve.fallback || {}),
        canvas: false,
        fs: false,
        path: false,
      };
    }

    if (config.mode === "development") {
      config.cache = false;
    }

    return config;
  },
};

export default nextConfig;
