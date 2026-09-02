import type { Metadata } from 'next';
import '../styles/globals.css';
import { ReactNode } from 'react';
import { Providers } from './providers';

export const metadata: Metadata = {
  title: 'Publishing Command Center',
  description: 'AI-powered music publishing data management',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body className="min-h-screen bg-[#0a0e1a] text-white antialiased">
        <Providers>
          {children}
        </Providers>
      </body>
    </html>
  );
}
