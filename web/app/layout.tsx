import './globals.css';
import type { Metadata } from 'next';

export const metadata: Metadata = {
  title: 'SnapTale — Every Picture Has a Story',
  description: 'No humans. Just everything else. SnapTale transforms photos of animals and everyday objects into hilarious persistent characters, stories, and universes.',
  openGraph: {
    title: 'SnapTale — Every Picture Has a Story',
    description: 'No humans. Just everything else.',
    type: 'website',
  }
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="en">
      <body className="antialiased selection:bg-snappink selection:text-white">
        {children}
      </body>
    </html>
  );
}
