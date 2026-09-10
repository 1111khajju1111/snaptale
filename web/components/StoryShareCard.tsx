import React from 'react';

interface StoryShareCardProps {
  characterName: string;
  species: string;
  storyTitle: string;
  punchline: string;
  imageUrl?: string;
  mode?: string;
}

export default function StoryShareCard({
  characterName,
  species,
  storyTitle,
  punchline,
  imageUrl,
  mode = 'snaptale'
}: StoryShareCardProps) {
  const isSnapPlus = mode === 'snapplus';

  return (
    <div className={`relative rounded-3xl overflow-hidden border p-6 max-w-md w-full mx-auto shadow-2xl transition-transform hover:scale-[1.02] ${
      isSnapPlus
        ? 'bg-gradient-to-b from-[#181224] to-[#0A0710] border-purple-800/40 text-white'
        : 'bg-gradient-to-b from-[#1E1B2E] to-[#120F1D] border-white/10 text-white'
    }`}>
      {/* Header Badge */}
      <div className="flex items-center justify-between mb-4">
        <span className={`text-xs font-black uppercase tracking-wider px-3 py-1 rounded-full ${
          isSnapPlus
            ? 'bg-purple-900/60 text-purple-300 border border-purple-500/40'
            : 'bg-yellow-400/20 text-yellow-300 border border-yellow-400/40'
        }`}>
          {isSnapPlus ? '🔞 SNAPTALE+' : '😂 SNAPTALE'}
        </span>
        <span className="text-xs font-semibold text-gray-400">
          {species.toUpperCase()}
        </span>
      </div>

      {/* Image Preview */}
      {imageUrl && (
        <div className="relative aspect-video w-full rounded-2xl overflow-hidden mb-4 bg-gray-900 border border-white/10">
          <img
            src={imageUrl}
            alt={characterName}
            className="w-full h-full object-cover"
          />
        </div>
      )}

      {/* Character and Story Title */}
      <div className="mb-4">
        <h4 className="text-xs uppercase tracking-widest text-snapyellow font-bold mb-1">
          {characterName}
        </h4>
        <h2 className="text-xl font-extrabold tracking-tight text-white line-clamp-2">
          {storyTitle}
        </h2>
      </div>

      {/* Punchline Box */}
      <div className="p-4 rounded-2xl bg-white/5 border border-white/10 mb-6 backdrop-blur-sm">
        <p className="text-sm italic font-medium text-gray-200">
          "{punchline}"
        </p>
      </div>

      {/* Watermark Branding */}
      <div className="border-t border-white/10 pt-3 flex items-center justify-between text-[11px] text-gray-400">
        <div className="flex items-center gap-1.5 font-bold">
          <span>📸</span>
          <span className="text-white tracking-wide font-black">SNAPTALE</span>
        </div>
        <span>Every Picture Has a Story.</span>
      </div>
    </div>
  );
}
