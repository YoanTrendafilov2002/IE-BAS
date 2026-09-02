import type { Metadata } from 'next';
import { Geist, Geist_Mono } from 'next/font/google';
import './globals.css';

const geistSans = Geist({
  variable: '--font-geist-sans',
  subsets: ['latin'],
});

const geistMono = Geist_Mono({
  variable: '--font-geist-mono',
  subsets: ['latin'],
});

export const metadata: Metadata = {
  metadataBase: new URL('https://earthcare-orbit-tracker.yoyowolf2002.chatgpt.site'),
  title: 'EarthCARE ATLID Target Data',
  description: 'Calculate when the modelled EarthCARE ATLID footprint passes within a selected kilometre radius of IE-BAS or another target.',
  openGraph: {
    title: 'EarthCARE ATLID Target Data',
    description: 'Validated OMM provenance, SGP4 propagation, 3° aft ATLID beam geometry, target distances, and UTC event tables.',
    images: [{ url: 'https://earthcare-orbit-tracker.yoyowolf2002.chatgpt.site/og.png', width: 1536, height: 1024, alt: 'EarthCARE ATLID Target Data' }],
  },
  twitter: {
    card: 'summary_large_image',
    title: 'EarthCARE ATLID Target Data',
    description: 'Scientific EarthCARE ATLID target-distance events and CSV export for IE-BAS.',
    images: ['https://earthcare-orbit-tracker.yoyowolf2002.chatgpt.site/og.png'],
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
      >
        {children}
      </body>
    </html>
  );
}
