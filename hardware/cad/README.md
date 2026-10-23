# CAD — HERMES node printable parts

**Concept, build-to-verify. Nothing here has been printed or fitted.**

| File | What it is |
|---|---|
| `hermes_parts.scad` | Parametric OpenSCAD source for the two printed parts: the direction-finding **array template** and a **mast clamp**. |

The rest of the node is bought, not printed (KrakenSDR, Raspberry Pi 5, IP66
enclosure, antennas) — see [`../bom-v1.md`](../bom-v1.md).

## Why an array *template*

`hardware/assembly.md` is blunt about two things that decide whether direction
finding works at all:

1. **The array radius must come from the band, not a guess** — it has to stay at
   or below half a wavelength or bearings wrap and become ambiguous.
   868 MHz → ~0.15 m, 433.92 MHz → ~0.31 m, 1240 MHz → ~0.11 m.
2. **Antenna 1 must be physically marked** — every bearing is measured from it.

The printed template builds both of those in: fixed 72° spacing at a radius you
set from the band, and a raised marker at antenna 1.

## How to build it

1. Install [OpenSCAD](https://openscad.org/) (free).
2. Open `hermes_parts.scad`.
3. Set the band radius: run
   `python -c "from czapla.doa import suggest_array_radius; print(suggest_array_radius(868e6))"`
   from `software/`, and put the result (in mm) into `array_radius_mm`.
4. **Measure your real antenna bulkhead and mast** and set `antenna_hole_mm` and
   `mast_d_mm`. The defaults are placeholders.
5. Choose `part` (`"array"`, `"clamp"`, or `"both"`), press **F6**, then
   **File → Export → STL**.
6. Print in **ASA or PETG** for outdoor UV and heat. PLA will warp on a mast.

## Before you trust it

- Dry-fit the bosses against a real SMA/N bulkhead before printing five.
- Check the printed radius with calipers; the geometry is only as good as the
  print, and a wrong radius silently biases every bearing.
- Record the radius and the antenna-1 direction in `hardware/results.md`.
