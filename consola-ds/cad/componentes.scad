// =====================================================================
//  CONSOLA DS DIY - MAQUETAS DE LOS COMPONENTES
//  Solo sirven para ver el montaje y comprobar que nada choca.
//  No se imprimen. Estan colocadas en su sitio (mitad de arriba cerrada).
// =====================================================================
include <params.scad>

EPS = 0.05;   // separacion minima para que las comprobaciones no den falsos choques

// Alturas de referencia
Z_PI = SUELO + PI_POSTE + EPS;                  // cara inferior de la placa de la Pi
Z_PANT_INF = H_INF - TAPA_T - PANT[2] - EPS;    // cara inferior de la pantalla de abajo
Z_PANT_SUP = Z_SUP0 + MARCO_T + EPS;            // cara del cristal de la pantalla de arriba (mira hacia abajo)
Z_SW_PLUNGER = H_INF - TAPA_T - CAP_HUELGO - CAP_PESTANA;   // donde apoya la pestana de los botones
Z_PERF = Z_SW_PLUNGER - SW[2];                  // cara superior de las placas perforadas

module caja(p, s) translate(p) cube(s);

// ---------------- Raspberry Pi 5 ----------------
module pi5() {
  translate([PI_POS[0], PI_POS[1], Z_PI]) {
    color("green") difference() {
      cube([PI_L, PI_W, PI_PCB]);
      for (a = PI_AGUJ) translate([a[0], a[1], -1]) cylinder(d = 2.7, h = 5, $fn = 16);
    }
    // USB + Ethernet
    color("silver") translate([PI_PUERTOS[0], PI_PUERTOS[1], PI_PCB])
      cube([PI_PUERTOS[2], PI_PUERTOS[3], PI_PUERTOS[4]]);
    // Active Cooler
    color("dimgray") translate([PI_VENT[0], PI_VENT[1], PI_PCB])
      cube([PI_VENT[2], PI_VENT[3], PI_VENT[4]]);
    // Cabezal GPIO
    color("black") translate([PI_GPIO[0], PI_GPIO[1], PI_PCB])
      cube([PI_GPIO[2], PI_GPIO[3], PI_GPIO[4]]);
    // USB-C y micro-HDMI en el borde delantero
    for (i = [0 : 2]) color("silver")
      translate([PI_CONEC_X[i] - (i == 0 ? 4.5 : 3.5), -1, PI_PCB])
        cube([i == 0 ? 9 : 7, 7, 3.5]);
  }
}

// ---------------- Pantallas ----------------
module pantalla() {
  // modulo con el cristal hacia +z
  color("black") translate([-PANT[0] / 2, -PANT[1] / 2, 0]) cube(PANT);
  color("royalblue") translate([PANT_AA_OFF[0] - PANT_AA[0] / 2, PANT_AA_OFF[1] - PANT_AA[1] / 2, PANT[2] - 0.2])
    cube([PANT_AA[0], PANT_AA[1], 0.21]);
}
module pantalla_inf() translate([PANT_C[0], PANT_C[1], Z_PANT_INF]) pantalla();
module pantalla_sup()   // cristal mirando hacia abajo (hacia la mitad de abajo)
  translate([PANT_C[0], PANT_C[1], Z_PANT_SUP + PANT[2]]) mirror([0, 0, 1]) pantalla();

// ---------------- Bateria ----------------
module celdas() {
  for (i = [0 : 1]) color("orange")
    translate([BAT_X + TOL + CELDA_D / 2 + i * (CELDA_D + 2 * TOL + SEPARADOR),
               BAT_Y + MUELLE, SUELO + CELDA_D / 2 + EPS])
      rotate([-90, 0, 0]) cylinder(d = CELDA_D, h = CELDA_L, $fn = 48);
}

// ---------------- Modulos ----------------
module modulos() {
  color("purple") caja([UPS_POS[0], UPS_POS[1], SUELO + EPS], UPS);
  color("red") caja([AMP_POS[0], AMP_POS[1], SUELO + EPS], AMP);
  color("teal") caja([ADC_POS[0], ADC_POS[1], SUELO + EPS], ADC);
  // interruptor deslizante pegado a la pared frontal
  color("white") translate([INTERR_X - INTERR[0] / 2, PARED + EPS, INTERR_Z - INTERR[2] / 2]) cube(INTERR);
}

// ---------------- Placas perforadas y pulsadores ----------------
function pos_botones_izq() = concat(
  [for (a = [0 : 3]) [CRUCETA_C[0] + CRUCETA_SW * cos(a * 90), CRUCETA_C[1] + CRUCETA_SW * sin(a * 90)]],
  [for (b = BOTONES_PEQ) if (b[0] < W / 2) [b[0], b[1]]]);
function pos_abxy() = [[ABXY_C[0], ABXY_C[1] + ABXY_SEP], [ABXY_C[0], ABXY_C[1] - ABXY_SEP],
                       [ABXY_C[0] - ABXY_SEP, ABXY_C[1]], [ABXY_C[0] + ABXY_SEP, ABXY_C[1]]];
function pos_botones_der() = concat(pos_abxy(), [for (b = BOTONES_PEQ) if (b[0] > W / 2) [b[0], b[1]]]);

module pulsador() {
  color("black") translate([-SW[0] / 2, -SW[1] / 2, 0]) cube([SW[0], SW[1], 3.5]);
  color("gray") cylinder(d = 3.5, h = SW[2] - 2 * EPS, $fn = 16);
}
module placa_perf(p) color("khaki") translate([p[0], p[1], Z_PERF - PERF_T - EPS]) cube([p[2], p[3], PERF_T]);

module botonera() {
  placa_perf(PERF_IZQ);
  placa_perf(PERF_DER);
  for (q = concat(pos_botones_izq(), pos_botones_der())) translate([q[0], q[1], Z_PERF]) pulsador();
  // pulsadores de L y R, pegados al soporte, mirando hacia atras
  for (x = LR_X) translate([x, LR_SOPORTE_Y + 2 + EPS, LR_Z]) rotate([-90, 0, 0]) pulsador();
}

// ---------------- LEDs, sensor, iman, altavoces ----------------
module leds() for (p = LED_POS) translate([p[0], p[1], H_INF - TAPA_T - 5]) {
  color("lime") cylinder(d = LED_D, h = 5 + TAPA_T - 0.3, $fn = 16);
  color("lime") cylinder(d = 3.8, h = 1, $fn = 16);
}
module sensor_hall() color("black") translate([HALL_POS[0] - 2, HALL_POS[1] - 1.5, H_INF - TAPA_T - 1.5 - EPS]) cube([4, 3, 1.5]);
module iman() color("silver") translate([IMAN_POS[0], IMAN_POS[1], Z_SUP0 + 0.6 + EPS]) cylinder(d = IMAN[0], h = IMAN[1], $fn = 24);
module altavoces() for (c = ALT_C) color("darkred")
  translate([c[0], c[1], Z_SUP0 + MARCO_T + EPS]) cylinder(d = ALT_D, h = ALT_H, $fn = 48);

// ---------------- Conjuntos ----------------
module componentes_inf() { pi5(); pantalla_inf(); celdas(); modulos(); botonera(); leds(); sensor_hall(); }
module componentes_sup() { pantalla_sup(); altavoces(); iman(); }
