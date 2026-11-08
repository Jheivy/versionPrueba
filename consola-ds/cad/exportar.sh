#!/usr/bin/env bash
# Genera los STL, las imagenes y comprueba el diseno.
# Uso:  ./exportar.sh            (todo)
#       ./exportar.sh stl        (solo piezas)
#       ./exportar.sh choques    (solo comprobaciones)
#       ./exportar.sh imagenes   (solo imagenes)
# Necesita: openscad (2021.01 o superior); para imagenes sin pantalla, xvfb-run.
set -u
cd "$(dirname "$0")"
QUE="${1:-todo}"
mkdir -p stl img registros

PIEZAS="base_inferior tapa_inferior puerta_bateria superior_marco superior_trasera botones prueba_bisagra prueba_botones"
CHOQUES="choque_inf choque_sup choque_botones choque_piezas choque_bisagra_0 choque_bisagra_90 choque_bisagra_max"
CAMA=180   # Bambu Lab A1 mini: 180 x 180 x 180 mm

XVFB=""
command -v xvfb-run >/dev/null && XVFB="xvfb-run -a -s -screen\ 0\ 1920x1080x24"

medidas() {   # imprime ancho x fondo x alto de un STL ASCII
  python3 - "$1" <<'EOF'
import sys
xs, ys, zs = [], [], []
for linea in open(sys.argv[1]):
    p = linea.split()
    if p and p[0] == "vertex":
        xs.append(float(p[1])); ys.append(float(p[2])); zs.append(float(p[3]))
if not xs:
    print("VACIO"); sys.exit()
print("%.1f %.1f %.1f %.2f" % (max(xs)-min(xs), max(ys)-min(ys), max(zs)-min(zs), min(zs)))
EOF
}

if [ "$QUE" = "todo" ] || [ "$QUE" = "stl" ]; then
  echo "== Piezas =="
  for p in $PIEZAS; do
    openscad -D "part=\"$p\"" -o "stl/$p.stl" consola.scad > "registros/$p.txt" 2>&1 &
  done
  wait
  fallo=0
  for p in $PIEZAS; do
    if grep -qiE "^ERROR|WARNING: (Object may not be a valid|.*undefined|.*unknown)" "registros/$p.txt" || [ ! -s "stl/$p.stl" ]; then
      echo "  [FALLO] $p (mirad registros/$p.txt)"; fallo=1; continue
    fi
    read -r ancho fondo alto zmin <<< "$(medidas "stl/$p.stl")"
    estado="OK"
    awk -v a="$ancho" -v f="$fondo" -v h="$alto" -v c="$CAMA" 'BEGIN{exit !(a<=c && f<=c && h<=c)}' || { estado="NO CABE"; fallo=1; }
    awk -v z="$zmin" 'BEGIN{exit !(z>-0.01 && z<0.01)}' || { estado="$estado (no apoya en z=0: $zmin)"; fallo=1; }
    printf "  [%s] %-18s %6s x %6s x %6s mm\n" "$estado" "$p" "$ancho" "$fondo" "$alto"
  done
  [ $fallo = 0 ] && echo "  Todas las piezas se generan y caben en la cama."
fi

if [ "$QUE" = "todo" ] || [ "$QUE" = "choques" ]; then
  echo "== Comprobaciones (deben salir vacias) =="
  for c in $CHOQUES; do
    openscad -D "part=\"$c\"" -o "registros/$c.stl" consola.scad > "registros/$c.txt" 2>&1 &
  done
  wait
  for c in $CHOQUES; do
    if grep -q "Current top level object is empty" "registros/$c.txt"; then
      echo "  [OK]     $c"
    elif grep -qi "^ERROR" "registros/$c.txt"; then
      echo "  [ERROR]  $c (mirad registros/$c.txt)"
    else
      read -r ancho fondo alto zmin <<< "$(medidas "registros/$c.stl")"
      if [ "$ancho" = "VACIO" ]; then
        echo "  [OK]     $c (solo se tocan en una arista, sin volumen)"
      else
        echo "  [CHOQUE] $c: zona de ${ancho} x ${fondo} x ${alto} mm (abrid registros/$c.stl)"
      fi
    fi
  done
fi

if [ "$QUE" = "todo" ] || [ "$QUE" = "imagenes" ]; then
  echo "== Imagenes =="
  render() {  # nombre parte camara
    eval $XVFB openscad -D "'part=\"$2\"'" -D ANG=110 -o "img/$1.png" --imgsize=1600,1100 \
      --camera="$3" --colorscheme=Tomorrow --projection=p consola.scad > "registros/img_$1.txt" 2>&1
  }
  render montaje_cerrado  montaje_cerrado  "82,44,22,58,0,340,440" &
  render montaje_abierto  montaje_abierto  "82,70,45,64,0,340,560" &
  render explosionado     explosionado     "82,44,50,62,0,330,620" &
  render interior         interior         "82,44,10,50,0,340,380" &
  render trasera          montaje_cerrado  "82,50,22,60,0,160,440" &
  wait
  ls -1 img/*.png 2>/dev/null | sed 's/^/  /'
fi
