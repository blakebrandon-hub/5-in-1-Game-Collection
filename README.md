# 🕹️ 4-in-1 Game Collection

> **AI-Powered Interactive Fiction** — Four narrative-driven games powered by a unified Python backend, built to work with Claude, GPT, and Gemini.

---

## Games

### Sprawl
*John is an operator who drifted too deep into the heavy-metal end of the trade and never found a clean way back. Now he works the Sprawl — contracts, deadlines, and whatever else comes his way.*

A cyberpunk noir experience with a live neural-link AI (`GHOST`) that monitors your vitals, hacks systems on your behalf, and degrades under pressure. Features a custom glyph engine that tracks strain, trace exposure, faction reputation, and inventory — all parsed silently from narrative output.

### Warden
*Stand against the Void as humanity's last defense. Master 32 ancient Words of power, forge oaths across four kingdoms, and hold the line between reality and oblivion.*

A dark fantasy RPG built around a strict magic system (The 32 Words, organized into four Circles), a Fracture mechanic that punishes over-casting, and a full HEMA-inspired combat doctrine embedded in the system prompt. The Bestiary and Grimoire are queryable in-game.

### Greywake
*A narrative-driven space adventure where your decisions echo across the cosmos. Explore alien worlds, navigate political intrigue, and uncover mysteries older than the stars.*

A space opera with a crew of five distinct characters, a faction standing system across eight factions, a ship upgrade and crew equipment economy, and an in-browser vector memory system (the Datacore) for long-term narrative recall. Features an in-game Fold Drive for sector travel.

### Black Ichor
*Scavenge the ruins. Fortify the Sanctuary. Fight the Ichor. In a world of liquid shadow, the caloric math is absolute. Survive a visceral, text-based reality where every resource is scarce and the silence is your only warning.*

A post-apocalyptic survival game with real resource pressure (HP, Pressure, Noise, Supplies), a base-building system, alchemy crafting, vow-based objectives, and procedural BGM that transitions between ambient and combat states.

---

## Architecture

All four games share a single Flask backend (`app.py`) with three AI endpoints:

| Endpoint | Purpose |
|---|---|
| `POST /api/chat` | Main narration — routes to Claude, Gemini, or GPT based on `NARRATOR_MODEL` |
| `POST /api/archive` | Memory compression — uses a fast model to summarize conversation history |
| `POST /api/painter` | Image generation — refines narrative text into a visual prompt, then calls Imagen or GPT Image |

The narrator model and image model are set via environment variables and can be swapped independently:

```bash
NARRATOR_MODEL=claude-sonnet-4-6   # or gemini-3.1-pro-preview / gpt-5.4
IMAGE_MODEL=gpt-image-1.5          # or imagen-4.0-generate-001
```

Each game frontend handles all game logic client-side (state, tag parsing, audio, UI) and calls the backend only for generation. The backend is stateless.

---

## AI Integration

All games are designed to work with the three major providers:

| Provider | Narrator | Archivist / Refiner |
|---|---|---|
| Anthropic | `claude-sonnet-4-6` | `claude-haiku-4-5` |
| Google | `gemini-3.1-pro-preview` | `gemini-flash-lite-latest` |
| OpenAI | `gpt-5.4` | `gpt-5.4-mini` |

Provider detection is automatic from the model name. Expensive models handle narration; fast models handle compression and image prompt refinement.

---

## Setup

**1. Clone and install dependencies**

```bash
git clone https://github.com/blakebrandon-hub/5-in-1-Game-Collection
cd 5-in-1-Game-Collection
pip install flask flask-cors anthropic openai google-genai
```

**2. Set environment variables**

```bash
export ANTHROPIC_API_KEY=your_key_here
export OPENAI_API_KEY=your_key_here      # optional
export GEMINI_API_KEY=your_key_here      # optional

export NARRATOR_MODEL=claude-sonnet-4-6
export IMAGE_MODEL=gpt-image-1.5
```

**3. Run the server**

```bash
python app.py
```

Open `http://localhost:5000` to reach the game selection hub.

---

## Screenshots

<details>
<summary><b>Sprawl</b></summary>
<br>
<img width="2560" alt="Sprawl gameplay screenshot" src="https://github.com/user-attachments/assets/abe3e982-aeae-4823-9431-345f94fa1cdc" />
</details>

<details>
<summary><b>Warden</b></summary>
<br>
<img width="1366" alt="Warden gameplay screenshot" src="https://github.com/user-attachments/assets/a34f7e5a-b218-4e2f-a277-e03028f79df2" />
</details>

<details>
<summary><b>Greywake</b></summary>
<br>
<img width="1366" alt="Greywake gameplay screenshot" src="https://github.com/user-attachments/assets/c73a3e53-65c1-403c-bed0-5e4a7e88552c" />
</details>

<details>
<summary><b>Black Ichor</b></summary>
<br>
<img width="1366" alt="Black Ichor gameplay screenshot" src="https://github.com/user-attachments/assets/19a22bff-ba14-43df-9ca0-21da4afb6ced" />
</details>

---

## Project Structure

```
/
├── app.py                          # Unified Flask backend
├── templates/
│   ├── index.html                  # Game selection hub
│   ├── templates_sprawl/
│   ├── templates_warden/
│   ├── templates_greywake/
│   └── templates_ichor/
└── static/
    ├── static_sprawl/
    ├── static_warden/
    ├── static_greywake/
    └── static_ichor/
```

Each game directory contains its own `index.html` with all game logic self-contained — state management, tag parsing, audio, and UI are handled entirely in the browser.

---

## Related

- **[4-in-1 AI Workspace](https://github.com/blakebrandon-hub/5-in-1-AI-Workspace)** — The AI development environment this project grew out of.

---

## License

Each game maintains its own licensing. Check individual repositories for details.

---

<img width="1366" height="768" alt="image" src="https://github.com/user-attachments/assets/d305cdb8-33ba-4d73-a024-3c8bff23d43e" />

