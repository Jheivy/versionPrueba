import 'package:ds_juntos/nucleo/lanzador.dart';
import 'package:ds_juntos/nucleo/red.dart';
import 'package:ds_juntos/nucleo/sistemas.dart';
import 'package:ds_juntos/nucleo/sync_decision.dart';
import 'package:flutter_test/flutter_test.dart';

void main() {
  group('sistemas', () {
    test('detecta el sistema por la extensión', () {
      expect(sistemaPorRuta('/roms/Pokemon Platino.NDS')?.id, 'nds');
      expect(sistemaPorRuta(r'C:\roms\Zelda.sfc')?.id, 'snes');
      expect(sistemaPorRuta('juego.gbc')?.nucleo, 'gambatte');
      expect(sistemaPorRuta('notas.txt'), isNull);
      expect(sistemaPorRuta('sin_extension'), isNull);
    });

    test('limpia el título del archivo', () {
      expect(tituloDesdeArchivo('/x/Pokemon - Platinum Version (USA) (Rev 1).nds'), 'Pokemon - Platinum Version');
      expect(tituloDesdeArchivo(r'C:\r\Mario_Kart_DS [b].nds'), 'Mario Kart DS');
    });

    test('URL de carátula codificada', () {
      final url = urlCaratula(sistemaPorId('nds')!, '/r/Mario Kart DS (Europe).nds');
      expect(url, startsWith('https://thumbnails.libretro.com/Nintendo%20-%20Nintendo%20DS/Named_Boxarts/'));
      expect(url, endsWith('Mario%20Kart%20DS%20(Europe).png'));
    });

    test('modo juntos por id', () {
      expect(ModoJuntos.desdeId('netplay'), ModoJuntos.netplay);
      expect(ModoJuntos.desdeId('raro'), ModoJuntos.turnos);
    });
  });

  group('sincronización', () {
    test('iguales o inexistentes: nada', () {
      expect(decidirSync(local: 'a', remoto: 'a', ultimoSincronizado: null), AccionSync.nada);
      expect(decidirSync(local: null, remoto: null, ultimoSincronizado: null), AccionSync.nada);
    });
    test('solo existe una copia', () {
      expect(decidirSync(local: 'a', remoto: null, ultimoSincronizado: null), AccionSync.subir);
      expect(decidirSync(local: null, remoto: 'b', ultimoSincronizado: null), AccionSync.bajar);
    });
    test('cambió solo un lado', () {
      expect(decidirSync(local: 'a', remoto: 'b', ultimoSincronizado: 'a'), AccionSync.bajar);
      expect(decidirSync(local: 'c', remoto: 'b', ultimoSincronizado: 'b'), AccionSync.subir);
    });
    test('cambiaron los dos: conflicto', () {
      expect(decidirSync(local: 'c', remoto: 'b', ultimoSincronizado: 'a'), AccionSync.conflicto);
      expect(decidirSync(local: 'c', remoto: 'b', ultimoSincronizado: null), AccionSync.conflicto);
    });
  });

  group('lanzador', () {
    test('Windows sin netplay', () {
      final o = ordenEscritorio(
        plataforma: Plataforma.windows,
        retroarch: r'C:\RetroArch-Win64\retroarch.exe',
        carpetaNucleos: r'C:\RetroArch-Win64\cores',
        nucleo: 'melondsds',
        rom: r'C:\roms\Pokemon.nds',
        archivoConfigExtra: r'C:\app\ds_juntos.cfg',
        apodo: 'Ana',
      );
      expect(o.ejecutable, r'C:\RetroArch-Win64\retroarch.exe');
      expect(o.argumentos, [
        '-L', r'C:\RetroArch-Win64\cores\melondsds_libretro.dll', r'C:\roms\Pokemon.nds',
        '--appendconfig', r'C:\app\ds_juntos.cfg', '--nick', 'Ana',
      ]);
    });

    test('Mac como anfitrión e invitado', () {
      final host = ordenEscritorio(
        plataforma: Plataforma.macos,
        retroarch: retroarchPorDefecto(Plataforma.macos),
        carpetaNucleos: '/Users/a/Library/Application Support/RetroArch/cores/',
        nucleo: 'snes9x',
        rom: '/roms/smw.sfc',
        archivoConfigExtra: '/tmp/x.cfg',
        apodo: 'Ana',
        netplay: const Anfitrion(),
      );
      expect(host.argumentos[1], '/Users/a/Library/Application Support/RetroArch/cores/snes9x_libretro.dylib');
      expect(host.argumentos.last, '--host');

      final inv = ordenEscritorio(
        plataforma: Plataforma.macos,
        retroarch: 'RetroArch',
        carpetaNucleos: '/c',
        nucleo: 'snes9x',
        rom: '/roms/smw.sfc',
        archivoConfigExtra: '/tmp/x.cfg',
        apodo: 'Leo',
        netplay: const Invitado('100.101.102.103'),
      );
      expect(inv.argumentos.sublist(inv.argumentos.length - 4), ['--connect', '100.101.102.103', '--port', '55435']);
    });

    test('intent de Android', () {
      final i = intentAndroid(paquete: 'com.retroarch.aarch64', nucleo: 'mgba', rom: '/storage/emulated/0/roms/a.gba');
      expect(i.actividad, actividadRetroArch);
      expect(i.extras['LIBRETRO'], '/data/data/com.retroarch.aarch64/cores/mgba_libretro_android.so');
      expect(i.extras['ROM'], '/storage/emulated/0/roms/a.gba');
      expect(i.extras.containsKey('CONFIGFILE'), isTrue);
    });

    test('ruta de la partida .srm', () {
      expect(rutaPartida('/saves', '/roms/Pokemon (USA).nds', Plataforma.android), '/saves/Pokemon (USA).srm');
      expect(rutaPartida(r'C:\s', r'C:\roms\Zelda.sfc', Plataforma.windows), r'C:\s\Zelda.srm');
    });

    test('config extra apunta a la carpeta de partidas', () {
      final c = configExtra(carpetaPartidas: '/sync', apodo: 'Ana');
      expect(c, contains('savefile_directory = "/sync"'));
      expect(c, contains('sort_savefiles_enable = "false"'));
    });
  });

  group('red', () {
    test('IP de Tailscale', () {
      expect(esIpTailscale('100.64.0.1'), isTrue);
      expect(esIpTailscale('100.127.255.254'), isTrue);
      expect(esIpTailscale('100.128.0.1'), isFalse);
      expect(esIpTailscale('192.168.1.10'), isFalse);
      expect(elegirIpTailscale(['192.168.1.4', '100.88.1.2']), '100.88.1.2');
      expect(elegirIpTailscale(['10.0.0.1']), isNull);
    });
    test('código de pareja', () {
      expect(codigoValido('ab3k9z'), isTrue);
      expect(codigoValido('AB0K9Z'), isFalse); // 0 se confunde con O
      expect(codigoValido('ABC'), isFalse);
    });
  });
}
