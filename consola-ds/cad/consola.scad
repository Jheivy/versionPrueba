// =====================================================================
//  CONSOLA DS DIY - CARCASA PARAMETRICA (OpenSCAD 2021.01 o superior)
//
//  Elegid la pieza con la variable `part` (o desde la linea de comandos:
//  openscad -D 'part="base_inferior"' -o base_inferior.stl consola.scad)
//
//  Piezas para imprimir (ya orientadas para la impresora):
//    base_inferior, tapa_inferior, puerta_bateria,
//    superior_marco, superior_trasera, botones,
//    prueba_bisagra, prueba_botones   <- imprimid estas primero
//  Vistas:  montaje_cerrado, montaje_abierto, explosionado, interior
//  Comprobaciones (deben salir vacias):
//    choque_inf, choque_sup, choque_botones, choque_piezas,
//    choque_bisagra_0, choque_bisagra_90, choque_bisagra_max
// =====================================================================
include <componentes.scad>

part = "montaje_cerrado";
ANG = 150;          // angulo para montaje_abierto
$fn = 40;

// ======================= UTILIDADES =======================
module rrect(w, d, r) {
  if (r > 0) translate([r, r]) offset(r = r) square([w - 2 * r, d - 2 * r]);
  else square([w, d]);
}
module contorno(inset = 0) translate([inset, inset]) rrect(W - 2 * inset, D - 2 * inset, max(R_ESQ - inset, 0.5));
module losa(z0, z1, inset = 0) translate([0, 0, z0]) linear_extrude(z1 - z0) contorno(inset);
module eje_x(x0, x1, d, fn = 40) translate([x0, EJE_Y, EJE_Z]) rotate([0, 90, 0]) cylinder(d = d, h = x1 - x0, $fn = fn);
module abrir(a) translate([0, EJE_Y, EJE_Z]) rotate([-a, 0, 0]) translate([0, -EJE_Y, -EJE_Z]) children();
// agujero con esquinas redondeadas que atraviesa una pared perpendicular a y
module hueco_y(x, z, w, h, y0, y1) translate([x, y0, z]) rotate([-90, 0, 0])
  linear_extrude(y1 - y0) offset(r = 1) square([w - 2, h - 2], center = true);
// idem, pared perpendicular a x
module hueco_x(y, z, w, h, x0, x1) translate([x0, y, z]) rotate([0, 90, 0])
  linear_extrude(x1 - x0) offset(r = 1) square([h - 2, w - 2], center = true);
module cruz2d() {
  square([CRUCETA_L, CRUCETA_A], center = true);
  square([CRUCETA_A, CRUCETA_L], center = true);
}

// ======================= BISAGRA =======================
// Nudillo con un refuerzo inclinado hacia su mitad (dir -1 abajo, +1 arriba)
// para que se imprima sin soportes. `crece` lo agranda para hacer el hueco.
module nudillo(k, dir, crece = 0) {
  x0 = k[0] - crece;
  x1 = k[1] + crece;
  hull() {
    eje_x(x0, x1, 2 * (KN_R + crece), 72);
    translate([x0, EJE_Y - PARED - crece, EJE_Z + dir * (2 * KN_R + crece) - 0.005])
      cube([x1 - x0, PARED + 2 * crece, 0.01]);
  }
}
module tuerca_m3(x0) {
  translate([x0, EJE_Y, EJE_Z]) rotate([0, 90, 0]) rotate([0, 0, 90])
    cylinder(d = M3_TUERCA_AF / cos(30), h = M3_TUERCA_H, $fn = 6);
  // ranura para meter la tuerca desde atras
  translate([x0, EJE_Y, EJE_Z - M3_TUERCA_AF / 2]) cube([M3_TUERCA_H, KN_R + 2, M3_TUERCA_AF]);
}
// Tornillos allen M3x20: cabeza en el nudillo de arriba (lado del hueco central),
// tuerca autoblocante en el nudillo de abajo.
module taladros_eje() {
  eje_x(KN_INF[0][0] - 2, KN_SUP[0][1] + 1, M3_D);
  eje_x(KN_SUP[0][1] - M3_CAB_P, KN_SUP[0][1] + 1, M3_CAB_D);
  tuerca_m3(KN_INF[0][0] + 0.6);
  eje_x(KN_SUP[1][0] - 1, KN_INF[1][1] + 2, M3_D);
  eje_x(KN_SUP[1][0] - 1, KN_SUP[1][0] + M3_CAB_P, M3_CAB_D);
  tuerca_m3(KN_INF[1][1] - 0.6 - M3_TUERCA_H);
}
module ranura_cable(z0, z1)
  translate([CABLE_X[0], D - CABLE_PROF, z0]) cube([CABLE_X[1] - CABLE_X[0], CABLE_PROF + 1, z1 - z0]);
// Barrido de un nudillo durante la apertura (0 .. APERTURA_MAX + 5 grados),
// para que el otro lado deje sitio en todo el recorrido.
module barrido(sgn) for (a = [0 : 15 : APERTURA_MAX]) hull() {
  abrir(sgn * a) children();
  abrir(sgn * min(a + 15, APERTURA_MAX + 5)) children();
}
module cortes_bisagra_inf() {     // lo que se quita a las piezas de abajo
  for (k = KN_SUP) barrido(1) nudillo(k, 1, KN_CLR);
  ranura_cable(H_INF - CABLE_ALTO, EJE_Z + 0.01);
  taladros_eje();
}
module cortes_bisagra_sup() {     // lo que se quita a las piezas de arriba
  for (k = KN_INF) barrido(-1) nudillo(k, -1, KN_CLR);
  ranura_cable(EJE_Z - 0.01, Z_SUP0 + CABLE_ALTO);
  taladros_eje();
}

// ======================= CUERPOS =======================
module cuerpo_inf() difference() {
  losa(0, H_INF);
  losa(SUELO, Z_CORTE, PARED);
}
module cuerpo_sup() difference() {
  losa(Z_SUP0, Z_SUP0 + H_SUP);
  losa(Z_SUP0 + MARCO_T, Z_SUP0 + H_SUP - TRASERA_T, PARED);
}
// ventana de la pantalla con chaflan hacia fuera (z_int: cara interior, z_ext: cara exterior)
module ventana(z_int, z_ext) {
  cx = PANT_C[0] + PANT_AA_OFF[0];
  cy = PANT_C[1] + PANT_AA_OFF[1];
  w = PANT_AA[0] + 2 * PANT_VENTANA_MARGEN;
  d = PANT_AA[1] + 2 * PANT_VENTANA_MARGEN;
  s = z_ext > z_int ? 1 : -1;
  module rect(m, z, h) translate([cx - w / 2 - m, cy - d / 2 - m, z]) cube([w + 2 * m, d + 2 * m, h]);
  hull() { rect(0, z_int - 0.005, 0.01); rect(1.2, z_ext - 0.005, 0.01); }
  rect(0, s > 0 ? z_int - 1 : z_int, 1);
  rect(1.2, s > 0 ? z_ext : z_ext - 1, 1);
}
// pestanas que centran la pantalla
module topes_pantalla(z0, z1) {
  x0 = PANT_C[0] - PANT[0] / 2;  x1 = PANT_C[0] + PANT[0] / 2;
  y0 = PANT_C[1] - PANT[1] / 2;  y1 = PANT_C[1] + PANT[1] / 2;
  for (y = [PANT_C[1] - 20, PANT_C[1] + 20]) {
    translate([x0 - TOL - 1.2, y - 4, z0]) cube([1.2, 8, z1 - z0]);
    translate([x1 + TOL, y - 4, z0]) cube([1.2, 8, z1 - z0]);
  }
  for (x = [PANT_C[0] - 25, PANT_C[0] + 25]) {
    translate([x - 4, y0 - TOL - 1.2, z0]) cube([8, 1.2, z1 - z0]);
    translate([x - 4, y1 + TOL, z0]) cube([8, 1.2, z1 - z0]);
  }
}

// ======================= BASE INFERIOR =======================
module bahia() {
  // tabique derecho, fondo y bloque del tornillo de la puerta
  translate([BAT_X + BAT_ANCHO, BAT_Y - 1, 0]) cube([1.2, BAT_LARGO + 1, SUELO + BAT_RIB_H]);
  translate([PARED - 0.5, BAT_Y + BAT_LARGO, 0]) cube([BAT_X + BAT_ANCHO + 1.2 - PARED + 0.5, 2, SUELO + BAT_RIB_H]);
  translate([PUERTA_TORN[0] - 4, BAT_Y + BAT_LARGO, 0]) cube([8, PUERTA_TORN[1] - BAT_Y - BAT_LARGO + 3.5, 8]);
}
module puerta_hueco() {
  translate([2.5, 2.5, -1]) cube([40, 77.5, 1 + PUERTA_REBAJE]);
  translate([BAT_X + 1, BAT_Y + 1.5, -1]) cube([BAT_ANCHO - 2, BAT_LARGO - 3, SUELO + 1.01]);
  translate([18, 0.8, PUERTA_REBAJE - 0.01]) cube([10, 3.8, SUELO - PUERTA_REBAJE + 0.11]);
  translate([PUERTA_TORN[0], PUERTA_TORN[1], -1]) cylinder(d = INSERTO_D, h = 1 + PUERTA_REBAJE + INSERTO_P);
}
module rejillas() for (i = [0 : 9])
  translate([PI_POS[0] + 10 + i * 5, PI_POS[1] + 9, -1]) cube([2, PI_W - 18, SUELO + 2]);
module huecos_paredes() {
  // frontal: USB-C de carga e interruptor
  hueco_y(UPS_POS[0] + UPS_USB[0], SUELO + UPS_USB[1], 11, 5.5, -1, PARED + 1);
  hueco_y(INTERR_X, INTERR_Z, 7.5, 4, -1, PARED + 1);
  // derecha: USB y Ethernet de la Pi
  hueco_x(PI_POS[1] + PI_PUERTOS[1] + PI_PUERTOS[3] / 2,
          (Z_PI + PI_PCB - 0.5 + Z_PI + PI_PCB + PI_PUERTOS[4] + 0.7) / 2,
          PI_PUERTOS[3] + 1, PI_PUERTOS[4] + 1.2, W - PARED - 1, W + 1);
  // trasera: gatillos L y R
  for (x = LR_X) hueco_y(x, LR_Z, LR_TAM[0] + 2 * TOL, LR_TAM[1] + 2 * TOL, D - PARED - 1, D + 1);
}
module base_inferior() {
  difference() {
    union() {
      intersection() {
        union() {
          intersection() { cuerpo_inf(); translate([-1, -1, -1]) cube([W + 2, D + 2, Z_CORTE + 1]); }
          for (p = TORN_INF) translate([p[0], p[1], 0]) cylinder(d = TORN_INF_D, h = Z_TORN);
          for (a = PI_AGUJ) translate([PI_POS[0] + a[0], PI_POS[1] + a[1], 0]) cylinder(d = 5.5, h = SUELO + PI_POSTE);
          bahia();
        }
        losa(-1, Z_CORTE);
      }
      for (k = KN_INF) nudillo(k, -1);
    }
    for (p = TORN_INF) translate([p[0], p[1], -1]) {
      cylinder(d = M2_D, h = Z_TORN + 2);
      cylinder(d = M2_CAB_D, h = Z_TORN - 4 + 1);
    }
    for (a = PI_AGUJ) translate([PI_POS[0] + a[0], PI_POS[1] + a[1], 0.8]) cylinder(d = M2_PILOTO, h = 10);
    puerta_hueco();
    rejillas();
    huecos_paredes();
    cortes_bisagra_inf();
  }
}

// ======================= TAPA INFERIOR =======================
module labio_tapa() for (t = LABIO_TRAMOS) {
  y = t[2] == "F" ? PARED + TOL : D - PARED - TOL - LABIO_T;
  translate([t[0], y, Z_CORTE - LABIO_H]) cube([t[1] - t[0], LABIO_T, LABIO_H + 0.01]);
}
module agujeros_botones() {
  translate([CRUCETA_C[0], CRUCETA_C[1], Z_CORTE - 1]) linear_extrude(TAPA_T + 2) offset(delta = TOL) cruz2d();
  for (q = pos_abxy()) translate([q[0], q[1], Z_CORTE - 1]) cylinder(d = ABXY_D + 2 * TOL, h = TAPA_T + 2);
  for (b = BOTONES_PEQ) translate([b[0], b[1], Z_CORTE - 1]) cylinder(d = BOT_PEQ_D + 2 * TOL, h = TAPA_T + 2);
  for (p = LED_POS) translate([p[0], p[1], Z_CORTE - 6]) cylinder(d = LED_D + 0.2, h = TAPA_T + 7);
}
module tapa_inferior() {
  difference() {
    union() {
      intersection() { cuerpo_inf(); translate([-1, -1, Z_CORTE]) cube([W + 2, D + 2, TAPA_T + 1]); }
      intersection() {
        union() {
          labio_tapa();
          for (p = TORN_INF) translate([p[0], p[1], Z_TORN + 0.1]) cylinder(d = 6, h = Z_CORTE - Z_TORN - 0.1 + 0.01);
          for (p = concat(PERF_IZQ_POSTES, PERF_DER_POSTES)) translate([p[0], p[1], Z_PERF]) cylinder(d = 4.5, h = Z_CORTE - Z_PERF + 0.01);
          topes_pantalla(Z_CORTE - PANT_TOPE_H, Z_CORTE + 0.01);
          for (x = LR_X) translate([x - LR_SOPORTE_ANCHO / 2, LR_SOPORTE_Y, LR_Z - 4.5])
            cube([LR_SOPORTE_ANCHO, 2, Z_CORTE - LR_Z + 4.5 + 0.01]);
          translate([HALL_POS[0] - 4, PARED + TOL, Z_CORTE - 4]) cube([8, HALL_POS[1] + 3 - PARED - TOL, 4.01]);
        }
        losa(0, H_INF, PARED + TOL);
      }
    }
    for (p = TORN_INF) translate([p[0], p[1], Z_TORN]) cylinder(d = INSERTO_D, h = INSERTO_P + 0.1);
    for (p = concat(PERF_IZQ_POSTES, PERF_DER_POSTES)) translate([p[0], p[1], Z_PERF - 1]) cylinder(d = M2_PILOTO, h = 5);
    translate([HALL_POS[0] - 2.2, HALL_POS[1] - 1.7, Z_CORTE - 5]) cube([4.4, 3.4, 5]);
    ventana(Z_CORTE, H_INF);
    agujeros_botones();
    for (t = TOPES) translate([t[0], t[1], H_INF - 0.4]) cylinder(d = 6, h = 1);   // marcas de los topes
    for (k = KN_INF) nudillo(k, -1, KN_CLR);
    cortes_bisagra_inf();
  }
}

// ======================= PUERTA DE LA BATERIA =======================
module puerta_bateria() difference() {
  union() {
    translate([2.5 + TOL, 2.5 + TOL, 0]) cube([40 - 2 * TOL, 77.5 - 2 * TOL, PUERTA_REBAJE - 0.05]);
    translate([BAT_X + 1 + TOL, BAT_Y + 1.5 + TOL, 0]) cube([BAT_ANCHO - 2 - 2 * TOL, BAT_LARGO - 3 - 2 * TOL, SUELO - 0.02]);
    translate([18 + TOL, 0.8 + TOL, PUERTA_REBAJE + 0.05]) cube([10 - 2 * TOL, 5.5, SUELO - PUERTA_REBAJE - 0.07]);
  }
  translate([PUERTA_TORN[0], PUERTA_TORN[1], -1]) cylinder(d = M2_D, h = 5);
}

// ======================= MITAD SUPERIOR =======================
module rejilla_altavoz(c) for (i = [-3 : 3], j = [-3 : 3]) {
  px = c[0] + i * 2.6 + (j % 2 == 0 ? 0 : 1.3);
  py = c[1] + j * 2.25;
  if (norm([px - c[0], py - c[1]]) < ALT_D / 2 - 2.5)
    translate([px, py, Z_SUP0 - 1]) cylinder(d = 1.5, h = MARCO_T + 2, $fn = 12);
}
module superior_marco() {
  zi = Z_SUP0 + MARCO_T;
  difference() {
    union() {
      intersection() { cuerpo_sup(); translate([-1, -1, Z_SUP0 - 1]) cube([W + 2, D + 2, MARCO_T + 1]); }
      intersection() {
        union() {
          difference() { losa(zi - 0.01, zi + LABIO_H, PARED + TOL); losa(zi - 1, zi + LABIO_H + 1, PARED + TOL + LABIO_T); }
          for (p = TORN_SUP) translate([p[0], p[1], zi - 0.01]) cylinder(d = TORN_SUP_D, h = H_SUP - MARCO_T - TRASERA_T - 0.1 + 0.01);
          topes_pantalla(zi - 0.01, zi + PANT_TOPE_H);
          for (c = ALT_C) translate([c[0], c[1], zi - 0.01]) difference() {
            cylinder(d = ALT_D + 2 * TOL + 2.4, h = ALT_H, $fn = 64);
            translate([0, 0, -1]) cylinder(d = ALT_D + 2 * TOL, h = ALT_H + 2, $fn = 64);
          }
          translate([IMAN_POS[0], IMAN_POS[1], zi - 0.01]) cylinder(d = IMAN[0] + 3, h = 1.6);
        }
        losa(Z_SUP0, Z_SUP0 + H_SUP, PARED + TOL);
      }
    }
    ventana(zi, Z_SUP0);
    for (c = ALT_C) rejilla_altavoz(c);
    translate([IMAN_POS[0], IMAN_POS[1], Z_SUP0 + 0.6]) cylinder(d = IMAN[0] + 0.3, h = 4);
    for (p = TORN_SUP) translate([p[0], p[1], Z_SUP0 + H_SUP - TRASERA_T - 0.1 - INSERTO_P]) cylinder(d = INSERTO_D, h = INSERTO_P + 1);
    for (k = KN_SUP) nudillo(k, 1, KN_CLR);
    cortes_bisagra_sup();
  }
}
module superior_trasera() {
  zt = Z_SUP0 + H_SUP - TRASERA_T;    // cara interior de la tapa exterior
  difference() {
    union() {
      intersection() { cuerpo_sup(); translate([-1, -1, Z_SUP0 + MARCO_T]) cube([W + 2, D + 2, H_SUP]); }
      for (k = KN_SUP) nudillo(k, 1);
      // almohadillas que aprietan la pantalla (con cinta de espuma de 1 mm)
      for (sx = [-1, 1], sy = [-1, 1])
        translate([PANT_C[0] + sx * (PANT[0] / 2 - 8), PANT_C[1] + sy * (PANT[1] / 2 - 8), Z_PANT_SUP + PANT[2] + 0.6])
          cylinder(d = 6, h = zt - (Z_PANT_SUP + PANT[2] + 0.6) + 0.01);
    }
    for (p = TORN_SUP) translate([p[0], p[1], zt - 1]) {
      cylinder(d = M2_D, h = TRASERA_T + 2);
      translate([0, 0, 1 + TRASERA_T - 1.2]) cylinder(d = M2_CAB_D, h = 2);
    }
    cortes_bisagra_sup();
  }
}

// ======================= BOTONES =======================
CAP_H = CAP_PESTANA + CAP_HUELGO + TAPA_T + CAP_SALE;
NUB = Z_SW_PLUNGER - Z_PERF - 0.25;   // pivote de la cruceta
module cap_redondo(d) {
  cylinder(d = d, h = CAP_H);
  cylinder(d = d + 2 * CAP_PEST_ANCHO, h = CAP_PESTANA);
}
module cap_cruceta() {
  linear_extrude(CAP_H) cruz2d();
  for (k = [0 : 2]) translate([0, 0, k * CAP_PESTANA / 3])
    linear_extrude(CAP_PESTANA / 3 + 0.01) offset(r = CAP_PEST_ANCHO * (3 - k) / 3) cruz2d();
  translate([0, 0, -NUB]) cylinder(d = 3, h = NUB + 0.01);
}
module cap_lr() {   // eje y hacia atras
  translate([-LR_TAM[0] / 2, 0, -LR_TAM[1] / 2]) cube([LR_TAM[0], CAP_H, LR_TAM[1]]);
  translate([-LR_TAM[0] / 2 - CAP_PEST_ANCHO, 0, -LR_TAM[1] / 2 - CAP_PEST_ANCHO])
    cube([LR_TAM[0] + 2 * CAP_PEST_ANCHO, CAP_PESTANA, LR_TAM[1] + 2 * CAP_PEST_ANCHO]);
}
module caps_montados() {
  translate([CRUCETA_C[0], CRUCETA_C[1], Z_SW_PLUNGER]) cap_cruceta();
  for (q = pos_abxy()) translate([q[0], q[1], Z_SW_PLUNGER]) cap_redondo(ABXY_D);
  for (b = BOTONES_PEQ) translate([b[0], b[1], Z_SW_PLUNGER]) cap_redondo(BOT_PEQ_D);
  for (x = LR_X) translate([x, D - PARED - CAP_HUELGO - CAP_PESTANA, LR_Z]) cap_lr();
}
// bandeja para imprimir: la cruceta boca abajo (su pestana va escalonada);
// los demas con la pestana sobre la cama
module botones() {
  translate([16, 16, CAP_H]) rotate([180, 0, 0]) cap_cruceta();
  for (i = [0 : 3]) translate([38 + i * 13, 10, 0]) cap_redondo(ABXY_D);
  for (i = [0 : len(BOTONES_PEQ) - 1]) translate([38 + (i % 5) * 12, 24 + floor(i / 5) * 12, 0]) cap_redondo(BOT_PEQ_D);
  for (i = [0 : 1]) translate([110, 8 + i * 14, 0]) rotate([90, 0, 0]) cap_lr();
}

// ======================= CONJUNTOS =======================
module mitad_inf() { base_inferior(); tapa_inferior(); puerta_bateria(); }
module mitad_sup() { superior_marco(); superior_trasera(); }
module montaje(a = 0, comp = true) {
  color("SteelBlue") base_inferior();
  color("LightSteelBlue") tapa_inferior();
  color("CadetBlue") puerta_bateria();
  color("WhiteSmoke") caps_montados();
  if (comp) componentes_inf();
  abrir(a) {
    color("LightSlateGray") superior_marco();
    color("SlateGray") superior_trasera();
    if (comp) componentes_sup();
  }
}
module explosionado() {
  color("CadetBlue") translate([0, 0, -25]) puerta_bateria();
  color("SteelBlue") base_inferior();
  pi5(); celdas(); modulos();
  translate([0, 0, 35]) {
    color("LightSteelBlue") tapa_inferior();
    pantalla_inf(); botonera(); leds(); sensor_hall();
    color("WhiteSmoke") translate([0, 0, 15]) caps_montados();
  }
  translate([0, 0, 85]) { color("LightSlateGray") superior_marco(); pantalla_sup(); altavoces(); iman(); }
  translate([0, 0, 115]) color("SlateGray") superior_trasera();
}

// ======================= PIEZAS DE PRUEBA =======================
module prueba_bisagra() {
  caja_b = [KN_INF[0][0] - 6, D - 14, 18];
  tam = [KN_SUP[0][1] - KN_INF[0][0] + 10, 22, 50];
  // trozo de la base (se imprime tal cual)
  translate([0, 0, -caja_b[2]]) {
    intersection() { base_inferior(); translate(caja_b) cube([tam[0], tam[1], EJE_Z - caja_b[2] + 0.01]); }
    translate([caja_b[0], caja_b[1], caja_b[2]]) cube([tam[0], D - caja_b[1], 2]);   // pie de apoyo
  }
  // trozo de la trasera de arriba, boca abajo
  translate([0, 2 * D + 30, Z_SUP0 + H_SUP]) rotate([180, 0, 0])
    intersection() { superior_trasera(); translate([caja_b[0], caja_b[1], EJE_Z]) cube([tam[0], tam[1], 30]); }
}
module prueba_botones() {
  // esquina izquierda de la tapa (cruceta y 4 botones), boca abajo, y sus botones
  translate([0, 2 * PERF_IZQ[1] + PERF_IZQ[3] + 2, H_INF]) rotate([180, 0, 0])
    intersection() { tapa_inferior(); translate([-1, PERF_IZQ[1] - 2, Z_PERF - 1]) cube([30, PERF_IZQ[3] + 4, 20]); }
  translate([45, 16, CAP_H]) rotate([180, 0, 0]) cap_cruceta();
  for (i = [0 : 3]) translate([38 + i * 10, 34, CAP_H]) rotate([180, 0, 0]) cap_redondo(BOT_PEQ_D);
}

// ======================= SELECTOR =======================
if (part == "base_inferior") base_inferior();
else if (part == "tapa_inferior") translate([0, D, H_INF]) rotate([180, 0, 0]) tapa_inferior();
else if (part == "puerta_bateria") puerta_bateria();
else if (part == "superior_marco") translate([0, 0, -Z_SUP0]) superior_marco();
else if (part == "superior_trasera") translate([0, D + KN_R + 1, Z_SUP0 + H_SUP]) rotate([180, 0, 0]) superior_trasera();
else if (part == "botones") botones();
else if (part == "prueba_bisagra") prueba_bisagra();
else if (part == "prueba_botones") prueba_botones();
else if (part == "montaje_cerrado") montaje(0);
else if (part == "montaje_abierto") montaje(ANG);
else if (part == "explosionado") explosionado();
else if (part == "interior") { color("SteelBlue") base_inferior(); componentes_inf(); }
// --- comprobaciones: el resultado debe estar VACIO ---
else if (part == "choque_inf") intersection() { mitad_inf(); componentes_inf(); }
else if (part == "choque_sup") intersection() { mitad_sup(); componentes_sup(); }
else if (part == "choque_botones") intersection() { union() { base_inferior(); tapa_inferior(); componentes_inf(); } caps_montados(); }
else if (part == "choque_piezas") union() {
  // (se separan 0,01 mm para no contar como choque las caras que solo se tocan)
  intersection() { base_inferior(); translate([0, 0, 0.01]) tapa_inferior(); }
  intersection() { base_inferior(); puerta_bateria(); }
  intersection() { superior_marco(); translate([0, 0, 0.01]) superior_trasera(); }
}
else if (part == "choque_bisagra_0") intersection() { union() { mitad_inf(); caps_montados(); componentes_inf(); } union() { mitad_sup(); componentes_sup(); } }
else if (part == "choque_bisagra_90") intersection() { union() { mitad_inf(); caps_montados(); } abrir(90) mitad_sup(); }
else if (part == "choque_bisagra_max") intersection() { union() { mitad_inf(); caps_montados(); } abrir(APERTURA_MAX) mitad_sup(); }
