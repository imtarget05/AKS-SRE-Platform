import type { Metadata } from 'next';
import './globals.css';
import { Navbar } from '../components/Navbar';

export const metadata: Metadata = {
  title: 'AKS SRE Platform Evidence Console',
  description:
    'Independent Next.js evidence viewer for AKS SRE Platform reliability metrics, SLO baselines, image digest immutability, and zero-downtime rollback drills.',
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en" className="dark">
      <body className="antialiased min-h-screen flex flex-col selection:bg-blue-600/30 selection:text-blue-200">
        <Navbar />
        <main className="flex-1 max-w-7xl w-full mx-auto px-4 sm:px-6 lg:px-8 py-8">
          {children}
        </main>
        <footer className="border-t border-slate-900 bg-slate-950/60 py-6 text-center text-xs text-slate-500">
          <div className="max-w-7xl mx-auto px-4">
            AKS-SRE-Platform Evidence Console • Cloudflare Workers Static Assets
            Preview • Verified Local & CI Artifacts
          </div>
        </footer>
      </body>
    </html>
  );
}
