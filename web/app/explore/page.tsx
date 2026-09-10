import Link from 'next/link';
import Navbar from '../../components/Navbar';
import Footer from '../../components/Footer';
import StoryShareCard from '../../components/StoryShareCard';

const SAMPLE_PUBLIC_STORIES = [
  {
    id: "story_dogesh_mars",
    characterName: "Dogesh Bhai",
    species: "Brown Indie Dog",
    storyTitle: "Dogesh Bhai: The Mars Incident",
    punchline: "Ticket price chusaka... I became Martian citizen 💀",
    imageUrl: "https://images.unsplash.com/photo-1543466835-00a7907e9de1?auto=format&fit=crop&w=800&q=80",
    mode: "snaptale",
    likes: 342,
    remixes: 48
  },
  {
    id: "story_chai_midnight",
    characterName: "Chai Cup Chari",
    species: "Cutting Chai Glass",
    storyTitle: "Midnight Philosophy at Irani Cafe",
    punchline: "12,000 startup pitches chusina gunde idi mowa!",
    imageUrl: "https://images.unsplash.com/photo-1517256064527-09c73fc73e38?auto=format&fit=crop&w=800&q=80",
    mode: "snaptale",
    likes: 215,
    remixes: 19
  },
  {
    id: "story_speedy_chetak",
    characterName: "Speedy Somanna",
    species: "1996 Bajaj Chetak",
    storyTitle: "Speedy Somanna vs The EV Gang",
    punchline: "Two-stroke smoke lo inka naatu power migile undi ra.",
    imageUrl: "https://images.unsplash.com/photo-1552519507-da3b142c6e3d?auto=format&fit=crop&w=800&q=80",
    mode: "snapplus",
    likes: 512,
    remixes: 83
  }
];

export default function ExplorePage() {
  return (
    <main className="min-h-screen flex flex-col">
      <Navbar />

      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-12 flex-1">
        <div className="mb-10 text-center md:text-left">
          <h1 className="text-4xl font-black text-white mb-2">Explore Stories</h1>
          <p className="text-gray-400">Discover trending non-human stories, characters, and multiverse remixes.</p>
        </div>

        {/* Filter Pills */}
        <div className="flex items-center gap-3 overflow-x-auto pb-6 mb-8 text-sm font-bold">
          <span className="px-5 py-2 rounded-full bg-snappink text-white shadow-md cursor-pointer">
            🔥 Trending
          </span>
          <span className="px-5 py-2 rounded-full bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10 cursor-pointer">
            😂 Funniest
          </span>
          <span className="px-5 py-2 rounded-full bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10 cursor-pointer">
            👻 Horror
          </span>
          <span className="px-5 py-2 rounded-full bg-white/5 hover:bg-white/10 text-gray-300 border border-white/10 cursor-pointer">
            🔀 Mutations & Remixes
          </span>
        </div>

        {/* Stories Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8">
          {SAMPLE_PUBLIC_STORIES.map((story) => (
            <div key={story.id} className="flex flex-col">
              <Link href={`/story/${story.id}`}>
                <StoryShareCard
                  characterName={story.characterName}
                  species={story.species}
                  storyTitle={story.storyTitle}
                  punchline={story.punchline}
                  imageUrl={story.imageUrl}
                  mode={story.mode}
                />
              </Link>
              <div className="flex items-center justify-between px-4 mt-3 text-xs text-gray-400">
                <span>❤️ {story.likes} Likes</span>
                <span>🔀 {story.remixes} Remixes</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      <Footer />
    </main>
  );
}
