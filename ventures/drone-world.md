# Drone world (working name)

Version 1, 2026-10-29. A separate project from SKARVIS, decided by Casper.
Replaces the "Flight lab" section that was in `product/simulator.md`.
**Nothing is built.** Sources for the facts below are in
`../research/sources.md` (section "Drone world").

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
| 3D engine | **Unreal Engine 5** | Photoreal scenes. Free to start; games pay 5 % royalty above USD 1 million gross revenue (Epic). A non-game product licensed to third parties may need different terms: check Epic's current EULA before charging money. |
| Real terrain | **Cesium for Unreal** (free, open source) + Cesium ion | Streams real terrain and photorealistic cities piece by piece, which is what makes 10×10 km workable. Google Photorealistic 3D Tiles come through Cesium ion; check Google's commercial terms before a paid product. |
| Flight | First our own simple quadcopter model (milestone 1), then the **real autopilot** (ArduPilot or PX4 in software-in-the-loop) | Realism comes from the real flight controller, not from our imitation of it. ArduPilot SITL accepts external physics over a JSON interface; PteroSim already joins it to Unreal Engine 5. |
| Controllers | EdgeTX radios over USB, gamepads, on-screen pad | EdgeTX radios offer a "USB Joystick (HID)" mode and need no driver; simulators see a generic joystick (USB ID 1209:4F54). |
| Builder numbers | Thrust, weight, hover throttle, flight time from parts | Needs real motor and propeller test tables. Until we have them, every computed figure is shown as an estimate. |
| Delivery | Windows download first | Streaming Unreal into a browser needs a graphics server per user: expensive. Reconsider after milestone 5. |
| Code home | Its own GitHub repository with Git LFS for large assets | Casper creates it and gives it a name. |

## Milestones (each one only after the previous works)

| # | Result anyone can see | Needs |
|---|---|---|
| M0 | Unreal Engine 5 + Cesium installed, empty project in the new repository | Windows PC with an NVIDIA RTX card; the repository |
| M1 | **First flight**: one quadcopter over 1×1 km of real terrain at a chosen place, flown with a gamepad or a USB radio | M0 |
| M2 | The same drone flown by real ArduPilot software (SITL) | M1 |
| M3 | Builder: choose frame, motors, propellers, battery; see the numbers and fly it | M2 + motor/propeller data |
| M4 | Upload: your own 3D model (glTF) plus a parts file | M3 |
| M5 | Accounts, free 1×1 km and paid 10×10 km areas | M4 + a company to take payments |

Gate before M5 (before spending on accounts, servers or payments): at least
five conversations with schools, flight training, government programmes or
drone builders, and at least one that says it would use or pay for it.

## Who does what

- **Claude**: writes most of the code (Unreal C++ and configuration, the
  builder maths, the ArduPilot link, the website for it), the docs and the
  plans. It cannot run Unreal Engine in its cloud session; for that it works
  in the project folder on Casper's PC through the Claude Desktop app (or
  `claude remote-control` in that folder).
- **Casper**: the PC, Unreal and Epic accounts, the repository, a 3D artist
  later (estimate: the realistic look at 10×10 km is months of work for an
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

1. Name of the project.
2. The first real place for M1 (somewhere you know; not a sensitive site).
3. Which PC: specs of the machine that will run Unreal.
