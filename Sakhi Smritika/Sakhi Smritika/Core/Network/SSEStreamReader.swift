import Foundation

/// Parses Server-Sent Events from the chat streaming endpoint.
struct SSEStreamReader {
    enum Event {
        case delta(String)
        case done(title: String?)
        case error(String)
        case unknown([String: Any])
    }

    /// Iterate SSE `data:` lines from an async byte stream.
    static func events(from bytes: URLSession.AsyncBytes) -> AsyncThrowingStream<Event, Error> {
        AsyncThrowingStream { continuation in
            Task {
                do {
                    var buffer = Data()
                    for try await byte in bytes {
                        buffer.append(byte)
                        while let range = buffer.range(of: Data("\n".utf8)) {
                            let lineData = buffer.subdata(in: buffer.startIndex..<range.lowerBound)
                            buffer.removeSubrange(buffer.startIndex..<range.upperBound)
                            guard let line = String(data: lineData, encoding: .utf8)?
                                .trimmingCharacters(in: .whitespacesAndNewlines),
                                !line.isEmpty
                            else { continue }

                            if line.hasPrefix("data:") {
                                let payload = line.dropFirst(5).trimmingCharacters(in: .whitespaces)
                                if let event = parse(payload: payload) {
                                    continuation.yield(event)
                                    if case .done = event { continuation.finish(); return }
                                    if case .error = event { continuation.finish(); return }
                                }
                            }
                        }
                    }
                    continuation.finish()
                } catch {
                    continuation.finish(throwing: error)
                }
            }
        }
    }

    private static func parse(payload: String) -> Event? {
        guard let data = payload.data(using: .utf8),
              let json = try? JSONSerialization.jsonObject(with: data) as? [String: Any]
        else { return .unknown(["raw": payload]) }

        if let delta = json["delta"] as? String {
            return .delta(delta)
        }
        if json["done"] as? Bool == true {
            return .done(title: json["title"] as? String)
        }
        if let error = json["error"] as? String {
            return .error(error)
        }
        return .unknown(json)
    }
}
