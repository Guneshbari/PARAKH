import type { Metadata, Viewport } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';
import { Providers } from './providers';
import { Header } from '@/components/layout/Header';
import { MobileNav } from '@/components/layout/MobileNav';

const geistSans = Geist({
  variable: '--font-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  title: 'PARAKH | Volatility-Aware Credit Assessment for the Invisible',
  description:
    'Explainable alternative credit intelligence evaluating cashflow patterns, gig platform resilience, and recovery dynamics.',
};

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  maximumScale: 1,
  themeColor: '#08090A',
};

const antiFlashScript = `
(function() {
  try {
    var stored = localStorage.getItem('parakh-theme');
    var theme = stored === 'light' ? 'light' : 'dark';
    if (theme === 'light') {
      document.documentElement.classList.add('light');
      document.documentElement.classList.remove('dark');
      document.documentElement.setAttribute('data-theme', 'light');
      document.documentElement.style.colorScheme = 'light';
    } else {
      document.documentElement.classList.add('dark');
      document.documentElement.classList.remove('light');
      document.documentElement.setAttribute('data-theme', 'dark');
      document.documentElement.style.colorScheme = 'dark';
    }
  } catch (e) {
    document.documentElement.classList.add('dark');
    document.documentElement.setAttribute('data-theme', 'dark');
  }
})();
`;

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} dark h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: antiFlashScript }} />
      </head>
      <body className="min-h-full flex flex-col bg-background text-foreground selection:bg-foreground/10 selection:text-foreground">
        <Providers>
          <Header />
          <main className="flex-1 pb-20 md:pb-0 flex flex-col min-h-0">{children}</main>
          <MobileNav />
        </Providers>
      </body>
    </html>
  );
}
