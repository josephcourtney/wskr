// Resolve only a uniquely titled, owned Kitty window; never screenshot a random desktop window.
import CoreGraphics
import Foundation

guard CommandLine.arguments.count == 3,
      let timeout = TimeInterval(CommandLine.arguments[2]),
      timeout > 0 else {
    fputs("usage: swift find_kitty_window.swift <exact-title> <timeout-seconds>\n", stderr)
    exit(2)
}

let title = CommandLine.arguments[1]
let deadline = Date().addingTimeInterval(timeout)

repeat {
    let windows = CGWindowListCopyWindowInfo(
        [.optionOnScreenOnly, .excludeDesktopElements],
        kCGNullWindowID
    ) as? [[String: Any]] ?? []

    let matches = windows.filter { window in
        let name = window[kCGWindowName as String] as? String ?? ""
        let owner = window[kCGWindowOwnerName as String] as? String ?? ""
        let layer = window[kCGWindowLayer as String] as? Int ?? -1
        return name == title && owner.lowercased().contains("kitty") && layer == 0
    }

    if matches.count > 1 {
        fputs("More than one Kitty window has the evidence title; refusing capture\n", stderr)
        exit(3)
    }
    if let only = matches.first, let identifier = only[kCGWindowNumber as String] as? Int {
        print(identifier)
        exit(0)
    }
    Thread.sleep(forTimeInterval: 0.25)
} while Date() < deadline

fputs("No uniquely titled Kitty window visible to CoreGraphics; check Screen Recording permission and window title\n", stderr)
exit(4)
