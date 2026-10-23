// ===========================================================================
// HERMES node — 3D-printable parts (parametric, OpenSCAD)
// ===========================================================================
// Version 1, 2026-10-22.  CONCEPT / BUILD-TO-VERIFY.
//
// These are the two parts the BOM calls "3D-printed adapters": the
// direction-finding array TEMPLATE (sets the exact antenna geometry) and a
// MAST CLAMP.  Everything else in the node is a bought part (KrakenSDR, Pi 5,
// IP66 box, antennas) and is NOT modelled here.
//
// Nothing here has been printed or fitted.  Before you print:
//   - Confirm the array radius for your band with
//       python -c "from czapla.doa import suggest_array_radius; \
//                  print(suggest_array_radius(868e6))"
//     (868 MHz -> ~0.15 m, 433.92 MHz -> ~0.31 m, 1240 MHz -> ~0.11 m;
//      the radius must stay <= half a wavelength or bearings wrap — see
//      hardware/assembly.md).
//   - Measure your actual SMA/N bulkhead and mast, and set the diameters below.
//
// How to use:
//   1. Open in OpenSCAD (free).  2. Set `part` below.  3. F6 to render.
//   4. Export STL (File > Export > STL) and slice for your printer.
//   Print in ASA or PETG for outdoor UV/temperature; PLA will not survive a mast.
// ===========================================================================

/* [What to render] */
part = "array";          // "array", "clamp", or "both"

/* [Array geometry] */
array_radius_mm   = 150;   // antenna ring radius. 868 MHz = 150. CHANGE PER BAND.
n_antennas        = 5;     // 5-element uniform circular array
antenna_hole_mm   = 6.5;   // SMA bulkhead clearance hole — MEASURE YOURS
boss_d_mm         = 16;    // material around each antenna hole
arm_w_mm          = 14;    // arm width
plate_t_mm        = 6;     // plate / arm thickness
hub_d_mm          = 46;    // central hub diameter

/* [Mast / mount] */
mast_d_mm         = 48;    // outside diameter of the mast/pole — MEASURE YOURS
bolt_hole_mm      = 5.5;   // M5 clearance
clamp_wall_mm     = 6;
clamp_h_mm        = 30;
ear_mm            = 18;

/* [Quality] */
$fn = 96;

// ---------------------------------------------------------------------------

module antenna_boss() {
    difference() {
        cylinder(h = plate_t_mm, d = boss_d_mm);
        translate([0, 0, -1]) cylinder(h = plate_t_mm + 2, d = antenna_hole_mm);
    }
}

module array_template() {
    // central hub with mast hole + 4 fixing holes
    difference() {
        cylinder(h = plate_t_mm, d = hub_d_mm);
        translate([0, 0, -1]) cylinder(h = plate_t_mm + 2, d = mast_d_mm * 0 + 22); // cable/mast pass-through
        for (a = [45:90:315])
            rotate([0, 0, a]) translate([hub_d_mm/2 - 7, 0, -1])
                cylinder(h = plate_t_mm + 2, d = bolt_hole_mm);
    }
    // arms + antenna bosses
    for (i = [0 : n_antennas - 1]) {
        a = i * 360 / n_antennas;
        rotate([0, 0, a]) {
            // arm
            translate([0, -arm_w_mm/2, 0])
                cube([array_radius_mm, arm_w_mm, plate_t_mm]);
            // boss at the ring radius
            translate([array_radius_mm, 0, 0]) antenna_boss();
        }
    }
    // antenna-1 marker: a small raised wedge so the zero-bearing reference
    // is physical (assembly.md: unmarked antenna 1 makes every bearing useless)
    translate([array_radius_mm + boss_d_mm/2, 0, 0])
        cylinder(h = plate_t_mm + 4, d1 = 7, d2 = 2);
}

module clamp_half() {
    r_in  = mast_d_mm / 2;
    r_out = r_in + clamp_wall_mm;
    difference() {
        union() {
            // half ring
            difference() {
                cylinder(h = clamp_h_mm, r = r_out);
                translate([0,0,-1]) cylinder(h = clamp_h_mm + 2, r = r_in);
                translate([-r_out-1, -r_out-1, -1]) cube([2*r_out+2, r_out+1, clamp_h_mm+2]);
            }
            // two bolt ears
            for (s = [-1, 1])
                translate([s*(r_out - 1), 0, 0])
                    translate([s < 0 ? -ear_mm : 0, -ear_mm, 0])
                        cube([ear_mm, ear_mm, clamp_h_mm]);
        }
        // ear bolt holes
        for (s = [-1, 1])
            translate([s*(r_out + ear_mm/2 - 1), -ear_mm/2, -1])
                cylinder(h = clamp_h_mm + 2, d = bolt_hole_mm);
    }
}

module mast_clamp() {
    // print two halves; they bolt around the mast
    clamp_half();
    translate([0, -mast_d_mm - 30, 0]) rotate([0, 0, 180]) clamp_half();
}

if (part == "array")      array_template();
else if (part == "clamp") mast_clamp();
else { array_template(); translate([0, array_radius_mm + 120, 0]) mast_clamp(); }
