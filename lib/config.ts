/**
 * Centralized API configuration for the Publishing Command Center frontend.
 * In the browser, defaults to relative '' to proxy through Next.js server on Vercel,
 * bypassing browser CORS restrictions completely.
 */

export function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '');
  }
  if (typeof window !== 'undefined') {
    return '';
  }
  return 'https://publishing-command-center-d6e1f2c72672.herokuapp.com';
}

export const API_BASE = getApiBase();
