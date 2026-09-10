# SnapTale API Reference

## Base URL
`/api/v1`

## Endpoints

### Health & Monitoring
- `GET /health` - Lightweight health check for Render & UptimeRobot (no AI calls).

### Authentication
- `POST /auth/register` - Create user profile and set preferred language.
- `POST /auth/login` - Verify token and return user profile.
- `POST /auth/logout` - Invalidate session.

### Photos & Human Detection
- `POST /photos/analyze` - Validates photo and performs strict server-side human detection. Rejects immediately if human is present.

### Characters
- `POST /characters` - Create character manually or from photo analysis.
- `GET /characters` - List user's characters (paginated).
- `GET /characters/{id}` - Retrieve character details, DNA, story history, and universe.
- `PUT /characters/{id}` - Update character details.
- `DELETE /characters/{id}` - Delete character and associated data.

### Stories & Branches
- `POST /stories/generate` - Start asynchronous story generation job.
- `GET /stories` - List stories (filter by mode, character, privacy).
- `GET /stories/{id}` - Retrieve story by ID.
- `POST /stories/{id}/mutate` - Create a new branch mutation (Funny, Horror, Space, etc.).
- `POST /stories/{id}/what-if` - Create a What If branch scenario.
- `POST /stories/{id}/continue` - Generate the next chapter in the storyline.
- `GET /stories/{id}/lore-tree` - Retrieve the lineage graph / tree for this story family.

### Chats & Topic Threads
- `POST /characters/{id}/chats` - Create a new topic chat thread.
- `GET /characters/{id}/chats` - List topic chat threads for character.
- `GET /chats/{id}` - Get chat metadata and message history.
- `POST /chats/{id}/messages` - Send message and receive character response.
- `DELETE /chats/{id}` - Delete chat thread.

### SnapTale+ Security
- `POST /snapplus/pin/setup` - Set initial 4-digit PIN (Argon2id hashed).
- `POST /snapplus/pin/verify` - Verify PIN to unlock protected chats for session.
- `PUT /snapplus/pin/change` - Change existing PIN.
- `POST /snapplus/pin/reset` - Reset PIN via account verification.

### Central Library & Pins
- `GET /library/search?q={query}` - Central search across characters, stories, chats, universes.
- `POST /pins` - Pin an item (max 10 per category).
- `DELETE /pins/{id}` - Unpin an item.

### Explore & Social
- `GET /explore` - Public moderated stories feed.
- `POST /stories/{id}/publish` - Publish story as unlisted or public.
- `POST /stories/{id}/like` - Like/unlike story.
- `POST /stories/{id}/comment` - Comment on story.
- `POST /stories/{id}/remix` - Remix story template with user's character.

### SnapFacts
- `GET /snapfacts/{subject}` - Retrieve verified real-world facts for photo subject.

### Jobs & WebSockets
- `GET /generation-jobs/{id}` - Poll job progress.
- `WebSocket /ws/jobs/{job_id}` - Real-time progress updates.
