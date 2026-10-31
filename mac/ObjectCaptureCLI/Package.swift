// swift-tools-version:5.9
import PackageDescription

let package = Package(
    name: "scan2print-object-capture",
    platforms: [.macOS(.v12)],
    targets: [
        .executableTarget(name: "scan2print-object-capture", path: "Sources/scan2print-object-capture")
    ]
)
