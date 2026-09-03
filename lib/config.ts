/**
 * Centralized API configuration for the Publishing Command Center frontend.
 * Defaults to the Heroku production backend unless overridden by NEXT_PUBLIC_API_URL.
 */

export function getApiBase(): string {
  if (process.env.NEXT_PUBLIC_API_URL) {
    return process.env.NEXT_PUBLIC_API_URL.replace(/\/+$/, '');
  }
  return 'https://publishing-command-center-d6e1f2c72672.herokuapp.com';
}

export const API_BASE = getApiBase();
