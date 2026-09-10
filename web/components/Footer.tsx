import Link from 'next/link';

export default function Footer() {
  return (
    <footer className="border-t border-white/10 bg-black/60 py-12 text-sm text-gray-400">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-4 gap-8 mb-8">
          <div className="col-span-1 md:col-span-2">
            <h3 className="text-white font-black text-lg mb-2">SNAPTALE</h3>
            <p className="text-gray-400 max-w-sm mb-4">
              Every Picture Has a Story. No humans. Just everything else.
              Turn photographs of animals, objects, and everyday things into persistent characters and alternate realities.
            </p>
            <div className="text-xs text-gray-500">
              © 2026 SnapTale Technologies. All rights reserved.
            </div>
          </div>
          <div>
            <h4 className="text-white font-bold mb-3">Product</h4>
            <ul className="space-y-2">
              <li><Link href="/explore" className="hover:text-white">Explore Stories</Link></li>
              <li><Link href="/developer" className="hover:text-white">Architecture & API</Link></li>
              <li><span className="text-snappink font-bold">😂 SnapTale Mode</span></li>
              <li><span className="text-purple-400 font-bold">🔞 SnapTale+ Mode</span></li>
            </ul>
          </div>
          <div>
            <h4 className="text-white font-bold mb-3">Legal & Safety</h4>
            <ul className="space-y-2">
              <li><Link href="/privacy" className="hover:text-white">Privacy Policy</Link></li>
              <li><Link href="/terms" className="hover:text-white">Terms of Service</Link></li>
              <li><span className="text-xs text-yellow-500">Zero-Retention Human Policy</span></li>
            </ul>
          </div>
        </div>
      </div>
    </footer>
  );
}
