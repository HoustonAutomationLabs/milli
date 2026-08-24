/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  poweredByHeader: false,
  /*
   * Ship the de-identified workbooks with the server bundle.
   *
   * `loadExportDataset` reads its directory from ER_EXPORT_DIR at request
   * time, so Next's file tracing cannot see the dependency — it only follows
   * statically analysable imports. On a serverless host the workbooks would
   * therefore be absent from the function and every request would fail with
   * "No cases loaded", which reads like a data problem rather than a
   * packaging one.
   *
   * Only data/demo is included. Real exports live in data/exports, which is
   * gitignored and must never reach a deployment.
   */
  outputFileTracingIncludes: {
    "/**": ["./data/demo/**"],
  },
  async headers() {
    // Security headers appropriate for an app that handles PHI.
    // Tighten CSP once the concrete asset/host set is known in Phase 0.
    return [
      {
        source: "/:path*",
        headers: [
          { key: "X-Frame-Options", value: "DENY" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=()" },
          {
            key: "Strict-Transport-Security",
            value: "max-age=63072000; includeSubDomains; preload",
          },
        ],
      },
    ];
  },
};

export default nextConfig;
