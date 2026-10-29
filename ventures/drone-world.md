# Drone world (working name)

Version 2, 2026-10-29. A separate project from SKARVIS, decided by Casper.
Replaces the "Flight lab" section that was in `product/simulator.md`.
**State: first playable browser prototype (M1)** in `drone-world/`, open
source (MIT). Generated landscape, estimated physics; not a real place yet and
not a certified simulator. Sources for the facts below are in
`../research/sources.md` (section "Drone world").

Change from version 1 (Casper, 2026-10-29: "it must be big open source project
with physics ... in browser ... and three.js"): browser first with three.js,
open source from day one; Unreal Engine 5 becomes the later photoreal client
and reuses the same C++ flight physics.

## What Casper wants

- A hyper-realistic 3D space where anyone can fly drones.
- **1×1 km free, 10×10 km paid** (for special drones or more space).
- A **builder**: put a drone together from parts and see how it flies.
- **Upload your own drone** (its 3D model and its parts) to test and fly it.
- **Real controller** if possible (the radio a pilot already owns), otherwise
  a gamepad or an on-screen controller.
- Audience: government programmes, schools, drone builders and operators
  who want to learn, test or show something. Not linked to SKARVIS radars.

## How it is built (decisions and why)

| Part | Choice | Why / source |
|---|---|---|
| 3D engine, now | **three.js** in the browser (open source, MIT) | Runs on the player's own computer, nothing to install, no cost per player. Unreal Engine has had no browser export since 4.24; Unreal in a browser means Pixel Streaming, where a GPU server renders for each player, so cost grows with every player online. |
| 3D engine, later | **Unreal Engine 5** client (U1) | The photoreal version. Compiles the same `core/cpp/DroneFlightModel.h`, so both clients fly the same. Games pay 5 % royalty above USD 1 million gross revenue (Epic); a non-game product licensed to third parties may need different terms: check Epic's current EULA before charging money. |
| Physics | One reference model in plain C++17 (`core/cpp`), ported line by line to JavaScript | A recorded C++ flight is replayed by the JS tests and must match to 1e-6 m, so the browser and Unreal never drift apart. |
| Real terrain | 3D Tiles: **3DTilesRendererJS** (three.js, open source, from NASA JPL) now; **Cesium for Unreal** in U1 | Streams terrain piece by piece, which is what makes 10×10 km workable. Google Photorealistic 3D Tiles and Cesium ion each need a key and have their own terms: check them before a paid product. |
| Flight, later | The **real autopilot** (ArduPilot or PX4 in software-in-the-loop) | Realism comes from the real flight controller, not from our imitation of it. ArduPilot SITL accepts external physics over a JSON interface. |
| Controllers | EdgeTX radios over USB, gamepads, keyboard, on-screen touch sticks | EdgeTX radios offer a "USB Joystick (HID)" mode and need no driver; the browser's Gamepad API sees them like a gamepad (USB ID 1209:4F54). Done in M1. |
| Builder numbers | Thrust, weight, hover throttle, flight time from parts | Needs real motor and propeller test tables. Until we have them, every computed figure is shown as an estimate. |
| Delivery | A static website (any static host); later a Windows download for the Unreal client | Free to host for the browser version. |
| Code home | Its own public GitHub repository (MIT) | Casper creates it and gives it a name; until then it lives in `drone-world/` here. |

## Milestones (each one only after the previous works)

| # | Result anyone can see | State |
|---|---|---|
| M1 | **First flight in the browser**: 1×1 km generated landscape (forest, lake, airfield, gates), camera drone and FPV quad, Hold / Angle / Acro, wind, collisions, keyboard / gamepad / USB radio / touch, own model upload (look only) | **Done (prototype), 2026-10-29** |
| M2 | Real places: 3D Tiles or open elevation data at a chosen place | Next |
| M3 | Builder: choose frame, motors, propellers, battery; see the numbers and fly it | Needs motor/propeller data |
| M4 | The same drone flown by real ArduPilot or PX4 software (SITL) | After M3 |
| M5 | Accounts, free 1×1 km and paid 10×10 km areas, multiplayer | M4 + a company to take payments |
| U1 | Unreal Engine 5 client with the same physics | Windows PC with an NVIDIA RTX card (Casper has an RTX 3060) |

Gate before M5 (before spending on accounts, servers or payments): at least
five conversations with schools, flight training, government programmes or
drone builders, and at least one that says it would use or pay for it.

## Who does what

- **Claude**: writes most of the code (the browser client and its tests, the
  shared physics, the builder maths, the ArduPilot link, later the Unreal
  C++), the docs and the plans. It builds and tests the browser client in its
  cloud session. It cannot run Unreal Engine there; for U1 it works in the
  project folder on Casper's PC through the Claude Desktop app (or
  `claude remote-control` in that folder).
- **Casper**: the public repository, testing with his own radio and PC,
  Unreal and Epic accounts for U1, a 3D artist later (estimate: the realistic look at 10×10 km is months of work for an
  experienced Unreal developer plus an artist; Claude shortens the coding,
  not the art).

## Lines it does not cross

- No weapons, payload release, strike or interceptor content.
- No SKARVIS sensor models and no "fly around a site's detection" mode.
- No detailed models of real critical infrastructure (power plants, military
  sites) in anything public, even if photoreal tiles show them.
- Flight training content follows EU drone rules; it does not replace the
  ULC exam.

## Open decisions for Casper

1. Name of the project (and of its public repository).
2. The first real place for M2 (somewhere you know; not a sensitive site).
3. Where the public version is hosted (GitHub Pages of the new repository is
   the simplest).
