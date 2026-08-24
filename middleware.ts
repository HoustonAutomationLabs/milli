import { NextResponse, type NextRequest } from "next/server";
import { AUTH_COOKIE_NAME } from "@/lib/auth";

/**
 * Edge guard: bounce unauthenticated requests to /login before they reach a
 * protected page. This is a coarse presence check only — the cookie's HMAC is
 * verified server-side in `getCurrentUser()` (node crypto isn't available in
 * the edge runtime). Defense in depth, not the sole gate.
 */
const PROTECTED = ["/dashboard", "/morning", "/caseload", "/compliance", "/training"];

export function middleware(req: NextRequest) {
  const { pathname } = req.nextUrl;
  const needsAuth = PROTECTED.some((p) => pathname === p || pathname.startsWith(`${p}/`));
  if (!needsAuth) return NextResponse.next();

  if (!req.cookies.get(AUTH_COOKIE_NAME)?.value) {
    const url = req.nextUrl.clone();
    url.pathname = "/login";
    return NextResponse.redirect(url);
  }
  return NextResponse.next();
}

export const config = {
  matcher: [
    "/dashboard/:path*",
    "/morning/:path*",
    "/caseload/:path*",
    "/compliance/:path*",
    "/training/:path*",
  ],
};
