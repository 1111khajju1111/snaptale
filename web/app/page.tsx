import Link from 'next/link';
import Navbar from '../components/Navbar';
import Footer from '../components/Footer';
import StoryShareCard from '../components/StoryShareCard';

export default function Home() {
  return (
    <main className="min-h-screen flex flex-col selection:bg-snappink selection:text-white">
      <Navbar />

      {/* Hero Section */}
      <section className="relative px-4 pt-20 pb-16 text-center max-w-5xl mx-auto flex flex-col items-center">
        <div className="inline-flex items-center gap-2 px-4 py-2 rounded-full bg-white/5 border border-white/10 text-xs font-bold text-snapyellow mb-8 backdrop-blur-md">
          <span>✨</span> Version 2.0 Production-Ready MVP
        </div>

        <h1 className="text-5xl md:text-7xl font-black tracking-tight text-white mb-6">
          Every Picture <br />
          <span className="bg-gradient-to-r from-snappink via-snapyellow to-snapcyan bg-clip-text text-transparent">
            Has a Story.
          </span>
        </h1>

        <p className="text-xl md:text-2xl text-gray-300 font-medium max-w-2xl mb-8">
          No humans. Just everything else.
        </p>

        <p className="text-base text-gray-400 max-w-xl mb-12">
          Take a photo of any animal, vehicle, chair, food, or gadget. SnapTale transforms it into a persistent fictional character, hilarious cinematic story, and interconnected universe.
        </p>

        {/* Primary CTA Buttons */}
        <div className="flex flex-wrap items-center justify-center gap-4 mb-16">
          <Link
            href="/explore"
            className="px-8 py-4 rounded-2xl bg-gradient-to-r from-snappink to-purple-600 hover:from-snappink/90 hover:to-purple-500 text-white font-extrabold text-lg shadow-xl shadow-snappink/25 transition-all hover:scale-105"
          >
            Explore Public Stories 🚀
          </Link>
          <a
            href="https://github.com"
            target="_blank"
            rel="noopener noreferrer"
            className="px-8 py-4 rounded-2xl bg-white/10 hover:bg-white/15 border border-white/10 text-white font-bold text-lg transition-all"
          >
            Download Android APK 📱
          </a>
        </div>

        {/* Live Card Spotlight */}
        <div className="w-full max-w-md mx-auto mb-16">
          <StoryShareCard
            characterName="Dogesh Bhai"
            species="Brown Indie Dog"
            storyTitle="Dogesh Bhai and the Last Metro"
            punchline="Earth lo EMI lu saripoledu ra... Mars ki shift ayya 💀"
            imageUrl="https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80"
            mode="snaptale"
          />
        </div>
      </section>

      {/* Two Experiences Showcase */}
      <section className="py-20 border-t border-white/10 bg-black/40 px-4">
        <div className="max-w-6xl mx-auto">
          <div className="text-center mb-16">
            <h2 className="text-3xl md:text-5xl font-black text-white mb-4">
              Two Experiences. One Application.
            </h2>
            <p className="text-gray-400 max-w-xl mx-auto text-base">
              Choose the general audience comedy engine or switch to mature dark comedy with gated PIN protection.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-8">
            {/* SnapTale */}
            <div className="p-8 rounded-3xl bg-gradient-to-b from-[#1C1829] to-[#120E1C] border border-white/10 relative overflow-hidden">
              <div className="inline-block px-4 py-1.5 rounded-full bg-yellow-400/20 text-yellow-300 font-black text-xs mb-4">
                😂 SNAPTALE (GENERAL AUDIENCE)
              </div>
              <h3 className="text-2xl font-black text-white mb-3">Absurd Comedy & Sarcasm</h3>
              <p className="text-gray-300 text-sm mb-6 leading-relaxed">
                Funny, chaotic, meme-style, and unexpected. Built with Telugu-English conversational "naatu naatu maatalu" code switching and classic comedy archetypes.
              </p>
              <div className="p-4 rounded-xl bg-black/40 border border-white/5 font-mono text-xs text-gray-300">
                "Bro literally cooked himself, yet still won the argument 💀"
              </div>
            </div>

            {/* SnapTale+ */}
            <div className="p-8 rounded-3xl bg-gradient-to-b from-[#24132B] to-[#14081A] border border-purple-800/40 relative overflow-hidden">
              <div className="inline-block px-4 py-1.5 rounded-full bg-purple-900/50 text-purple-300 font-black text-xs mb-4 border border-purple-500/30">
                🔞 SNAPTALE+ (MATURE EXPERIENCE)
              </div>
              <h3 className="text-2xl font-black text-white mb-3">Dark Comedy & Thriller</h3>
              <p className="text-gray-300 text-sm mb-6 leading-relaxed">
                Savage humor, horror, psychological undertones, and adult mystery. Protected behind strict age gating and a 4-digit Argon2id private chat PIN.
              </p>
              <div className="p-4 rounded-xl bg-black/40 border border-purple-500/20 font-mono text-xs text-purple-200">
                "Target located... Situation full ga out of control ayipoyindi ra!"
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Non-Negotiable Human Rejection Rule */}
      <section className="py-20 px-4 max-w-5xl mx-auto text-center">
        <div className="p-8 md:p-12 rounded-3xl bg-gradient-to-r from-red-950/30 to-purple-950/30 border border-red-500/20">
          <div className="text-4xl mb-4">🚫</div>
          <h3 className="text-2xl md:text-3xl font-black text-white mb-4">
            The Non-Negotiable Human Image Rule
          </h3>
          <p className="text-gray-300 text-base max-w-2xl mx-auto mb-6">
            SnapTale is strictly for non-humans. Any photo containing a person, face, or selfie is rejected server-side before vision AI or character persistence, and immediately purged.
          </p>
          <div className="inline-flex items-center gap-3 px-6 py-3 rounded-full bg-black/60 border border-white/10 text-sm font-semibold text-gray-300">
            <span>Dog = Accepted ✅</span>
            <span className="text-gray-600">•</span>
            <span>Chair = Accepted ✅</span>
            <span className="text-gray-600">•</span>
            <span className="text-red-400">Dog + Person = Rejected 🚫</span>
          </div>
        </div>
      </section>

      <Footer />
    </main>
  );
}
