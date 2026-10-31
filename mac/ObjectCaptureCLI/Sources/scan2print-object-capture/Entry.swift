// Uso: scan2print-object-capture <carpeta_fotos> <carpeta_salida> [preview|reduced|medium|full|raw]
// Reconstruye una malla con la fotogrametría de Apple (RealityKit / Object Capture).
// Requiere macOS 12+ en Apple Silicon (o GPU con >= 4 GB y raytracing).
import Foundation
import RealityKit

@main
struct Entry {
    static func fail(_ msg: String) -> Never {
        FileHandle.standardError.write(Data((msg + "\n").utf8))
        exit(1)
    }

    static func main() async {
        let a = CommandLine.arguments
        guard a.count >= 3 else {
            fail("uso: scan2print-object-capture <carpeta_fotos> <carpeta_salida> [preview|reduced|medium|full|raw]")
        }
        let input = URL(fileURLWithPath: a[1], isDirectory: true)
        let output = URL(fileURLWithPath: a[2], isDirectory: true)
        let detail: PhotogrammetrySession.Request.Detail
        switch a.count > 3 ? a[3] : "medium" {
        case "preview": detail = .preview
        case "reduced": detail = .reduced
        case "full": detail = .full
        case "raw": detail = .raw
        default: detail = .medium
        }
        guard PhotogrammetrySession.isSupported else {
            fail("Object Capture no está soportado en este Mac")
        }
        do {
            try FileManager.default.createDirectory(at: output, withIntermediateDirectories: true)
            var config = PhotogrammetrySession.Configuration()
            config.sampleOrdering = .unordered
            config.featureSensitivity = .normal
            let session = try PhotogrammetrySession(input: input, configuration: config)
            // URL de carpeta => OBJ + MTL + texturas (el backend busca *.obj).
            try session.process(requests: [.modelFile(url: output, detail: detail)])
            for try await o in session.outputs {
                switch o {
                case .requestProgress(_, let f):
                    print(String(format: "progreso %.0f%%", f * 100)); fflush(stdout)
                case .requestError(_, let e):
                    fail("error de reconstrucción: \(e)")
                case .processingComplete:
                    print("listo"); exit(0)
                default: break
                }
            }
        } catch {
            fail("error: \(error)")
        }
    }
}
