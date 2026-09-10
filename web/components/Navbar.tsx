import Link from 'next/link';

export default function Navbar() {
  return (
    <header className="sticky top-0 z-50 backdrop-blur-md bg-black/40 border-b border-white/10">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
        <Link href="/" className="flex items-center gap-2 group">
          <div className="w-10 h-10 rounded-xl bg-gradient-to-tr from-snappink via-snapyellow to-snapcyan flex items-center justify-center text-xl font-black text-black shadow-lg shadow-snappink/20 group-hover:scale-105 transition-transform">
            📸
          </div>
          <div>
            <span className="text-xl font-extrabold tracking-tight bg-gradient-to-r from-white via-white/90 to-white/60 bg-clip-text text-transparent">
              SNAPTALE
            </span>
            <span className="text-[10px] uppercase font-bold tracking-widest block text-snapyellow">
              No Humans. Just Everything Else.
            </span>
          </div>
        </Link>

        <nav className="hidden md:flex items-center gap-6 text-sm font-medium">
          <Link href="/explore" className="text-gray-300 hover:text-white transition-colors">
            Explore
          </Link>
          <Link href="/developer" className="text-gray-300 hover:text-white transition-colors">
            Developer & API
          </Link>
          <Link href="/privacy" className="text-gray-300 hover:text-white transition-colors">
            Privacy
          </Link>
        </nav>

        <div className="flex items-center gap-3">
          <Link
            href="/explore"
            className="px-4 py-2 rounded-full bg-gradient-to-r from-snappink to-purple-600 hover:from-snappink/90 hover:to-purple-500 text-white font-bold text-sm shadow-md transition-all hover:scale-105"
          >
            Download App
          </Link>
        </div>
      </div>
    </header>
  );
}
