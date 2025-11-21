import '../styles/globals.css';
import { ReactNode } from 'react';
import NavBar from '@/components/NavBar';

export const metadata = {
  title: 'Carbon Offset Land Analyzer',
  description: 'Phase 1 MVP',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen text-gray-900 bg-gradient-to-b from-zinc-50 via-white to-zinc-50">
        <div className="mx-auto max-w-7xl p-4">
          <NavBar />
          {children}
        </div>
      </body>
    </html>
  );
}
