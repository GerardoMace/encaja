# Encaja

Small puzzle games for mobile browsers, each written in plain HTML, CSS and JavaScript (one file per game, no dependencies, no build step).

| Game | Play |
|------|------|
| **Encaja**: 8×8 block puzzle | https://gerardomace.github.io/encaja/ |
| **Colonia**: puzzle levels on Conway's Game of Life | https://gerardomace.github.io/encaja/colonia/ |

## Encaja

Drag the three pieces onto the 8×8 board. A full row or column clears and scores points. Clearing lines on consecutive moves builds a combo multiplier. The game ends when no piece fits.

## How it is built

- Everything is drawn on a single `<canvas>`, scaled for the device pixel ratio.
- Pointer Events handle touch and mouse. On touch screens the dragged piece floats above the finger so it stays visible.
- Sound effects are synthesized with the Web Audio API; there are no audio files.
- The best score and the game in progress are saved in `localStorage`.
- The tray generator retries until at least one of the three pieces fits, so a new set is never dead on arrival.

## Colonia

You plant a few cells inside a marked zone, press *Crecer* (grow) and watch the colony evolve under Conway's rules (B3/S23). Each level asks the colony to reach a target, survive a number of generations, or avoid poison cells. Rocks never come alive.

Every level was checked by a brute-force solver that simulates every possible planting. That confirms each level can be solved and that random planting rarely works: on the glider levels fewer than 1% of plantings win. The in-game hint reveals one solution found by that solver, one cell at a time.

The interface of both games is in Spanish.
