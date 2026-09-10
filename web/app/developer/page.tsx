import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';

export default function DeveloperPage() {
  return (
    <main className="min-h-screen flex flex-col">
      <Navbar />

      <div className="max-w-5xl mx-auto px-4 py-12 flex-1">
        <h1 className="text-4xl font-black text-white mb-4">Developer & Architecture Guide</h1>
        <p className="text-gray-400 mb-8">Production-ready MVP specification and technical reference for SnapTale.</p>

        <div className="space-y-8 text-gray-300 text-sm leading-relaxed">
          <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
            <h2 className="text-xl font-bold text-white mb-3">Architecture Stack</h2>
            <ul className="list-disc list-inside space-y-1 text-gray-300">
              <li><strong>Mobile Application:</strong> Flutter + Dart (Android APK & iOS ready)</li>
              <li><strong>Backend API:</strong> FastAPI + Python (Render deployment ready)</li>
              <li><strong>Database:</strong> PostgreSQL on Aiven (asyncpg + SQLAlchemy)</li>
              <li><strong>Auth & Storage:</strong> Supabase Auth & Storage</li>
              <li><strong>Web Application:</strong> Next.js + React + Tailwind CSS (Vercel ready)</li>
              <li><strong>Monitoring:</strong> UptimeRobot on lightweight <code className="text-snapyellow">GET /health</code></li>
            </ul>
          </div>

          <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
            <h2 className="text-xl font-bold text-white mb-3">Strict Server-Side Human Detection</h2>
            <p className="mb-2">Before any vision analysis, character persistence, or story generation occurs:</p>
            <pre className="p-4 rounded-xl bg-black/60 font-mono text-xs text-snapyellow overflow-x-auto">
{`POST /api/v1/photos/analyze
Headers: Authorization: Bearer <token>
Body: Multipart form-data with photo

Human Detected?
├── YES -> HTTP 422 Unprocessable Entity
│          Response: "🚫 SnapTale can't use photos containing people."
│          Temp file deleted immediately; 0 database records.
└── NO  -> Proceed to non-human visual metadata extraction.`}
            </pre>
          </div>

          <div className="p-6 rounded-2xl bg-white/5 border border-white/10">
            <h2 className="text-xl font-bold text-white mb-3">SnapTale+ 4-Digit Chat PIN Security</h2>
            <p>SnapTale+ private chat threads are encrypted behind a user-configured 4-digit PIN:</p>
            <ul className="list-disc list-inside space-y-1 mt-2">
              <li>PINs are hashed using Argon2id with salt. Plaintext is never stored, logged, or sent to AI models.</li>
              <li>Brute-force protection: 5 consecutive failed attempts trigger an automated 15-minute temporary lockout.</li>
            </ul>
          </div>
        </div>
      </div>

      <Footer />
    </main>
  );
}
