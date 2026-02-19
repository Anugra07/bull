import '../styles/globals.css';
import { ReactNode } from 'react';
import NavBar from '@/components/NavBar';

export const metadata = {
  title: 'Offset Guesser - Carbon Offset Land Analyzer',
  description: 'Analyze land, estimate carbon potential, and make climate projects real with AI-powered geospatial analysis',
};

export default function RootLayout({ children }: { children: ReactNode }) {
  return (
    <html lang="en">
      <body className="min-h-screen text-[var(--ink)] antialiased">
        <div className="min-h-screen flex flex-col app-shell">
          <NavBar />
          <main className="flex-1 relative z-10">
            {children}
          </main>
          <footer className="mt-16 border-t-2 border-[var(--line)] bg-[var(--surface)] py-10 relative z-10">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <div className="grid gap-2 text-center text-sm text-[var(--muted)]">
                <p className="font-semibold tracking-wide text-[var(--ink)] uppercase">Offset Guesser</p>
                <p>Earth Engine-based carbon intelligence for project screening and planning.</p>
                <p className="text-xs">© 2026 Offset Guesser. Open/public-data-first carbon analysis.</p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
