## Photorealistic Doom

### Make Doom look like a movie — in real time

Create a real-time neural filter that transforms pixelated Doom graphics into photorealistic, cinematic imagery — think classic Doom rendered like Alien.

### Core insight
Traditional super-resolution trains on bicubic downsampling. Doom doesn’t look like that. By training on deterministically pixelated movie frames (Floyd–Steinberg/Bayer/Atkinson dithering, palette restriction, pixel grid), we generate perfect synthetic LR/HR pairs that map “Doom-like pixels” back to film-like reality.

### What we’re building
- A Doom emulator with an integrated neural post-process:
  1) Capture the emulator framebuffer (320×200 baseline)
  2) Enhance with an ESRGAN-derived model on Apple’s Neural Engine (Core ML FP16)
  3) Display via a low-latency Metal path
- A data pipeline that converts cinematic footage into deterministic “Doom-like” pixels for paired training.

### Targets
- 60 FPS at 2×–4× upscale
- <20 ms end-to-end latency
- <2 GB memory, <15% CPU; >80% Neural Engine utilization

### Okay, so step one is I want to just...
I'm trying to figure out how to automatically create the palette and see examples in the web-based UI within this package. I'd like to update the repo so I can upload a screenshot as a target, and it will automatically figure out the palette and other effects to use. Do you think it's possible to just upload a Doom screenshot and have it work, or is that too complicated?
Workflow (high level)
- Data: Extract cinematic frames → apply deterministic pixelation (dithering + palette + pixel grid) → build LR/HR pairs → train ESRGAN variant → convert to Core ML FP16.
- Emulator: Fork Chocolate Doom → hook framebuffer → async inference on NE → present with Metal → hotkey toggle original/enhanced.



