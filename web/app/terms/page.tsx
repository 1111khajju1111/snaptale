import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';

export default function TermsPage() {
  return (
    <main className="min-h-screen flex flex-col">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 py-12 flex-1 text-gray-300 text-sm leading-relaxed">
        <h1 className="text-3xl font-black text-white mb-6">Terms of Service</h1>

        <div className="space-y-6">
          <section className="p-6 rounded-2xl bg-white/5 border border-white/10">
            <h2 className="text-lg font-bold text-white mb-2">1. Permitted Content</h2>
            <p>
              SnapTale is an imagination toy designed for animals, everyday objects, food, vehicles, gadgets, and non-human things. Attempting to bypass human detection or upload unauthorized surveillance content is strictly prohibited.
            </p>
          </section>

          <section className="p-6 rounded-2xl bg-white/5 border border-white/10">
            <h2 className="text-lg font-bold text-white mb-2">2. SnapTale+ Age Gate & Maturity Guidelines</h2>
            <p>
              SnapTale+ is restricted to eligible mature users. While darker comedy, thrillers, and stronger language are supported, sexually explicit content, non-consensual exploitation, and harmful content remain strictly blocked.
            </p>
          </section>
        </div>
      </div>

      <Footer />
    </main>
  );
}
