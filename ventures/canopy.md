# Canopy drones (working name)

Version 1, 2026-10-29. A separate project from SKARVIS. Casper wants it;
this file records the concept, the hard parts and the cheapest way to test
it. **Nothing is built and nothing is measured.**

## The idea

Four drones fly in formation holding a sheet of light material between them
and hover over a person or a place:
- **VIP privacy**: cover a person from cameras above (including drones).
- **Accident scenes**: cover victims from onlookers while rescuers work.
- **Events and film**: shade, rain cover, a moving backdrop.

**Excluded:** hiding military equipment from reconnaissance (it is military
equipment under licence) and hiding any activity from police or authorities.

## Why it is harder than it looks (engineering judgement, not measured)

1. **Four drones, one sheet.** Drones that share one flexible load pull on
   each other; when one moves, the others feel it. This needs coordinated
   flight control, not four independent drones.
2. **Wind.** A sheet big enough to cover a person or a car is a sail. A gust
   pulls the formation sideways; rotor downwash makes the sheet flap.
3. **Flight time.** Batteries carry the drones plus the sheet; expect short
   hover times (estimate), so swaps or a tether become part of the product.
4. **Safety over people.** The product exists to hover over people. If one
   drone fails, the sheet and three drones come down on the person it covers.
5. **Rules.** In the EU open category a drone must not fly over assemblies
   of people (Regulation 2019/947). Flying over people needs the specific
   category: an operational authorisation from ULC based on a risk
   assessment (SORA). Aircraft of 3 m or more over assemblies of people fall
   into the certified category. A lawyer and ULC confirm the route before
   any flight with people underneath.

## Cheapest way to find out if it works

| Step | What | Cost | Gate to the next step |
|---|---|---|---|
| 1 | Simulate it in the drone world: four drones, cloth physics, wind | Software only | The formation holds the sheet in simulated gusts |
| 2 | Talk to buyers: fire brigade (PSP), police, event security, VIP protection firms, film productions | Time | At least two say what they would pay for and under which conditions |
| 3 | Indoor prototype: four small drones, a very light sheet, nobody underneath | Small (to price on the day) | Stable hover and a safe landing when one drone is switched off |
| 4 | Talk to ULC about the authorisation route | Time | A written route that a buyer can live with |

No money goes into hardware before step 2 says yes.

## Open decisions for Casper

1. Name.
2. First buyer type to talk to (recommendation: fire brigade or accident
   response, because the need and the buyer are clear).
