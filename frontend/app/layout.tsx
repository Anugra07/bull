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
      <body className="min-h-screen bg-gradient-to-br from-slate-50 via-white to-slate-50 text-gray-900 antialiased">
        <div className="min-h-screen flex flex-col">
          <NavBar />
          <main className="flex-1">
            {children}
          </main>
          <footer className="border-t border-gray-200 bg-white/50 backdrop-blur-sm py-8 mt-16">
            <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8">
              <div className="text-center text-sm text-gray-600">
                <p className="font-semibold text-gray-900 mb-2">Offset Guesser</p>
                <p>Powered by Google Earth Engine & Advanced Geospatial Analysis</p>
                <p className="mt-2 text-xs text-gray-500">© 2024 Offset Guesser. Making carbon offset projects accessible.</p>
              </div>
            </div>
          </footer>
        </div>
      </body>
    </html>
  );
}
