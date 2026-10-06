# Encaja

A block puzzle game for mobile browsers, written in plain HTML, CSS and JavaScript (one file, no dependencies, no build step).

**Play:** https://gerardomace.github.io/encaja/

Drag the three pieces onto the 8×8 board. A full row or column clears and scores points. Clearing lines on consecutive moves builds a combo multiplier. The game ends when no piece fits.

## How it is built

- Everything is drawn on a single `<canvas>`, scaled for the device pixel ratio.
- Pointer Events handle touch and mouse. On touch screens the dragged piece floats above the finger so it stays visible.
- Sound effects are synthesized with the Web Audio API; there are no audio files.
- The best score and the game in progress are saved in `localStorage`.
- The tray generator retries until at least one of the three pieces fits, so a new set is never dead on arrival.

The interface is in Spanish.
