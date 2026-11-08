// =====================================================================
//  CONSOLA DS DIY - MEDIDAS (unica fuente de verdad)
//  Todas las medidas en milimetros.
//  Ejes: x = ancho (izquierda -> derecha), y = fondo (desde el borde del
//  usuario hacia la bisagra), z = alto (desde la base hacia arriba).
//  Origen: esquina delantera-izquierda-inferior de la mitad de abajo.
//  La mitad de arriba se dibuja CERRADA, encima de la de abajo.
//
//  Este archivo tambien lo lee planos.py: usad solo numeros, listas,
//  textos entre comillas y operaciones + - * / con nombres ya definidos.
//
//  (!) = medida estimada: medidla con un calibre y corregidla antes de
//        imprimir las piezas grandes.
// =====================================================================

// ------------------------- GENERAL -------------------------
TOL = 0.3;          // holgura por lado entre piezas (ajustar con las piezas de prueba)
W = 164;            // ancho de la consola
D = 88;             // fondo de cada mitad (sin contar la bisagra)
H_INF = 33;         // alto de la mitad de abajo
H_SUP = 14;         // alto de la mitad de arriba
R_ESQ = 8;          // radio de las esquinas vistas desde arriba
PARED = 2;          // grosor de las paredes
SUELO = 2;          // grosor del suelo
TAPA_T = 2;         // grosor de la cara de los botones
MARCO_T = 2;        // grosor del marco de la pantalla de arriba
TRASERA_T = 2;      // grosor de la cara exterior de la tapa de arriba
LABIO_H = 2;        // labio de centrado entre piezas
LABIO_T = 1.2;
// Tramos del labio de la tapa de abajo: x desde, x hasta, "F" (pared frontal) o "T" (trasera)
LABIO_TRAMOS = [[30, 130, "F"], [10, 38, "T"], [126, 152, "T"]];
HUECO = 2;          // separacion entre mitades cerradas (los botones sobresalen 1,6)
Z_SUP0 = H_INF + HUECO;       // cara inferior de la mitad de arriba (cerrada)
Z_CORTE = H_INF - TAPA_T;     // plano entre base_inferior y tapa_inferior
Z_TORN = 25;        // donde se separan los postes de los tornillos de cierre

// ------------------------- BISAGRA -------------------------
// Eje en la arista trasera, en mitad del hueco entre mitades.
KN_R = 5.5;         // radio de los nudillos
EJE_Y = D;
EJE_Z = H_INF + HUECO / 2;
KN_CLR = 0.4;       // holgura entre nudillos
KN_INF = [[39.6, 49.6], [114.4, 124.4]];   // nudillos de la mitad de abajo (x desde, x hasta)
KN_SUP = [[50, 62], [102, 114]];           // nudillos de la mitad de arriba
M3_D = 3.4;         // agujero del eje (tornillo allen M3x20)
M3_CAB_D = 6.2;     // cabeza del tornillo
M3_CAB_P = 3;       // profundidad del avellanado de la cabeza
M3_TUERCA_AF = 5.8; // tuerca M3 autoblocante (entre caras + holgura)
M3_TUERCA_H = 4.3;
CABLE_X = [63, 101];    // hueco central para el cable plano y los cables de altavoces
CABLE_PROF = 9;         // cuanto entra la ranura hacia delante
CABLE_ALTO = 6;         // alto de la ranura en cada mitad
APERTURA_MAX = 150;     // angulo de apertura comprobado (grados)

// ------------------------- TORNILLOS DE CIERRE -------------------------
// Mitad de abajo: 3 tornillos M2x8 desde el suelo hasta insertos en la tapa
// (la esquina delantera izquierda la ocupa la bateria; ahi centra el labio).
TORN_INF = [[5, 82], [158.5, 8], [158.5, 83.4]];
TORN_INF_D = 6.6;   // diametro del poste
// Mitad de arriba: M2x6 desde la cara exterior hasta insertos en el marco.
TORN_SUP = [[5.5, 5.5], [158.5, 5.5], [5.5, 74], [158.5, 74]];
TORN_SUP_D = 6;
M2_D = 2.4;         // paso del tornillo M2
M2_CAB_D = 4.2;     // cabeza del tornillo M2
M2_PILOTO = 1.8;    // agujero para atornillar M2 directamente al plastico
INSERTO_D = 3.2;    // agujero para inserto termico M2 (mirad la medida de vuestro kit)
INSERTO_P = 4.5;

// ------------------------- PANTALLAS (Waveshare 4,3" DSI) -------------------------
PANT = [105.9, 68.1, 8.9];  // ancho, fondo, grosor del modulo (manual del fabricante)
PANT_AA = [95.0, 54.0];     // (!) area visible
PANT_AA_OFF = [0, 0];       // (!) desplazamiento del area visible respecto al centro
PANT_C = [W / 2, 41];       // centro de la pantalla (igual en las dos mitades)
PANT_VENTANA_MARGEN = 0.6;  // margen de la ventana alrededor del area visible
PANT_TOPE_H = 3;            // altura de las pestanas que centran la pantalla

// ------------------------- RASPBERRY PI 5 -------------------------
PI_L = 85;
PI_W = 56;
PI_PCB = 1.6;
PI_POS = [76, 24];          // esquina delantera-izquierda de la placa
PI_POSTE = 2;               // altura de los postes bajo la placa
PI_AGUJ = [[3.5, 3.5], [61.5, 3.5], [3.5, 52.5], [61.5, 52.5]];
PI_PUERTOS = [64, 2, 23, 52, 16];   // bloque USB+Ethernet: x, y (en placa), largo, ancho, alto
PI_VENT = [3, 4, 61, 42.5, 15];     // (!) Active Cooler: x, y, largo, ancho, ALTO sobre la placa
PI_GPIO = [7, 49.5, 51, 5.2, 8.5];  // cabezal GPIO: x, y, largo, ancho, alto
PI_CONEC_X = [11.2, 25.8, 39.2];    // USB-C y micro-HDMI (borde delantero de la placa)

// ------------------------- BATERIA (2 x 18650 en paralelo) -------------------------
CELDA_D = 18.6;
CELDA_L = 65.2;
MUELLE = 3.5;               // espacio para cada contacto de muelle
BAT_X = 3;                  // bahia: borde izquierdo
BAT_Y = 3;                  // bahia: borde delantero
SEPARADOR = 1.2;            // tabique entre las dos celdas
BAT_ANCHO = 2 * (CELDA_D + 2 * TOL) + SEPARADOR;
BAT_LARGO = CELDA_L + 2 * MUELLE;
BAT_RIB_H = 12;             // altura de los tabiques de la bahia
PUERTA_REBAJE = 1.2;        // grosor de la pestana de la puerta
PUERTA_TORN = [23, 77.5];   // tornillo M2 de la puerta

// ------------------------- MODULOS -------------------------
UPS = [26, 50, 12];         // (!) modulo 18650 UPS: ancho x, largo y, alto
UPS_POS = [49.5, 3];
UPS_USB = [13, 3.5];        // (!) centro del USB-C: x desde el borde izquierdo, z sobre su base
AMP = [18, 19, 3];          // MAX98357A
AMP_POS = [82, 4];
ADC = [28, 17, 3];          // ADS1115 (lee el nivel de bateria)
ADC_POS = [104, 4];
INTERR = [8.6, 3.6, 3.5];   // interruptor deslizante SS12D00
INTERR_X = 150;             // centro en x, en la pared frontal
INTERR_Z = 9;

// ------------------------- BOTONES -------------------------
SW = [6, 6, 4.3];           // pulsador 6x6, alto total con el boton
PERF_T = 1.6;               // grosor de la placa perforada
CAP_SALE = 1.6;             // cuanto sobresalen los botones
CAP_PESTANA = 1.2;          // pestana que impide que el boton se salga
CAP_PEST_ANCHO = 1.2;
CAP_HUELGO = 0.3;           // hueco entre la pestana y la cara interior
CRUCETA_C = [15.5, 52];
CRUCETA_L = 22;
CRUCETA_A = 7.5;
CRUCETA_SW = 7.25;          // distancia del centro a cada pulsador de la cruceta
ABXY_C = [148.25, 52];
ABXY_SEP = 8.5;
ABXY_D = 6.5;
BOT_PEQ_D = 6;
// Botones pequenos: x, y, nombre
BOTONES_PEQ = [[9, 34, "SWAP"], [22, 34, "HOME"], [9, 22, "GUARDAR"], [22, 22, "RAPIDO"],
               [143, 26, "START"], [156, 26, "SELECT"],
               [140, 74, "VOL-"], [148.75, 74, "VOL+"], [157.5, 74, "POWER"]];
PERF_IZQ = [3, 12, 24, 54];       // placa perforada izquierda: x, y, ancho, fondo
PERF_DER = [136.5, 12, 25, 66];   // placa perforada derecha
PERF_IZQ_POSTES = [[5.5, 14.5], [24.5, 14.5], [5.5, 63.5], [24.5, 63.5]];
PERF_DER_POSTES = [[139.5, 14.5], [159, 14.5], [139.5, 66.5], [159, 66.5]];
// Gatillos L y R en la pared trasera
LR_TAM = [18, 4.5];               // ancho (x) y alto (z) del gatillo
LR_Z = 24.5;                      // centro en z
LR_X = [19.5, 144.5];             // centros en x de L y R
LR_SOPORTE_Y = 78.2;              // cara delantera del soporte del pulsador (2 mm de grueso)
LR_SOPORTE_ANCHO = 20;
TOPES = [[6, 10], [158, 10]];     // topes adhesivos de 2 mm en la cara de la tapa (marcas en el marco)

// ------------------------- LEDS, IMAN Y SENSOR -------------------------
LED_D = 3;
LED_POS = [[8, 74], [16, 74]];    // encendido, bateria
HALL_POS = [16, 5];               // sensor A3144 (mitad de abajo)
IMAN = [5, 2];                    // iman 5x2 (mitad de arriba)
IMAN_POS = [16, 5];

// ------------------------- ALTAVOCES (mitad de arriba) -------------------------
ALT_D = 20;
ALT_H = 4.5;
ALT_C = [[15.5, 41], [148.5, 41]];
