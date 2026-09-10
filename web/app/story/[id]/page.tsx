import Link from 'next/link';
import Navbar from '../../../components/Navbar';
import Footer from '../../../components/Footer';
import StoryShareCard from '../../../components/StoryShareCard';

export default function StoryDetailPage({ params }: { params: { id: string } }) {
  return (
    <main className="min-h-screen flex flex-col">
      <Navbar />

      <div className="max-w-4xl mx-auto px-4 py-12 flex-1 w-full">
        <Link href="/explore" className="inline-flex items-center gap-2 text-sm text-gray-400 hover:text-white mb-6">
          ← Back to Explore
        </Link>

        <div className="grid grid-cols-1 md:grid-cols-2 gap-8 items-start mb-12">
          <div>
            <StoryShareCard
              characterName="Dogesh Bhai"
              species="Brown Indie Dog"
              storyTitle="Dogesh Bhai: The Mars Incident"
              punchline="Ticket price chusaka... I became Martian citizen 💀"
              imageUrl="https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80"
              mode="snaptale"
            />
          </div>

          <div className="p-6 rounded-3xl bg-white/5 border border-white/10">
            <h2 className="text-2xl font-black text-white mb-4">Dogesh Bhai: The Mars Incident</h2>
            
            <div className="space-y-3 mb-6 text-sm text-gray-300 leading-relaxed">
              <p><strong>Setup:</strong> Idi evaroo expect cheyyani scene in Mars space base.</p>
              <p><strong>Conflict:</strong> Earth loan recovery agents sent drone satellites to Mars orbit.</p>
              <p><strong>Twist:</strong> Dogesh Bhai had already bought the satellite company using cryptocurrency!</p>
              <p><strong>Climax:</strong> Bro cooked the entire Martian fleet with 360-degree parotta maneuvers.</p>
            </div>

            <div className="p-4 rounded-2xl bg-black/40 border border-white/10 mb-6">
              <span className="text-xs uppercase font-bold text-snapyellow block mb-1">Character Archetype</span>
              <span className="text-white font-bold">Overconfident Hero</span>
              <p className="text-xs text-gray-400 mt-1">Sarcasm: 88% • Telugu Slang: 78% • English Mix: 35%</p>
            </div>

            <div className="flex flex-col gap-3">
              <button className="w-full py-3 rounded-xl bg-gradient-to-r from-snappink to-purple-600 font-bold text-white shadow-md hover:scale-[1.02] transition-transform">
                Open in SnapTale App 📱
              </button>
              <button className="w-full py-3 rounded-xl bg-white/10 hover:bg-white/15 border border-white/10 font-bold text-white transition-all">
                Copy Share Link 🔗
              </button>
            </div>
          </div>
        </div>
      </div>

      <Footer />
    </main>
  );
}
