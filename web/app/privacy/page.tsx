import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';

export default function PrivacyPage() {
  return (
    <main className="min-h-screen flex flex-col">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 py-12 flex-1 text-gray-300 text-sm leading-relaxed">
        <h1 className="text-3xl font-black text-white mb-6">Privacy Policy</h1>
        
        <div className="space-y-6">
          <section className="p-6 rounded-2xl bg-white/5 border border-white/10">
            <h2 className="text-lg font-bold text-white mb-2">1. Zero-Retention Human Photo Policy</h2>
            <p>
              SnapTale strictly prohibits photographs containing humans or people. When an uploaded photo is detected to contain any human, the temporary file is unlinked immediately and deleted from our servers. No character, story, image, or database record is created.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-white/5 border border-white/10">
            <h2 className="text-lg font-bold text-white mb-2">2. Default Privacy is Private</h2>
            <p>
              All stories, characters, universe members, and chat threads created by users are private by default. They are visible exclusively to the authenticated account owner unless explicitly published as Unlisted or Public.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-white/5 border border-white/10">
            <h2 className="text-lg font-bold text-white mb-2">3. Complete Account and Data Deletion</h2>
            <p>
              Users may permanently delete their account and all associated characters, stories, branch lineage, and chat histories at any time via <code className="text-snapyellow">DELETE /api/v1/account</code> or within the mobile settings screen.
            </p>
          </section>
        </div>
      </div>

      <Footer />
    </main>
  );
}
