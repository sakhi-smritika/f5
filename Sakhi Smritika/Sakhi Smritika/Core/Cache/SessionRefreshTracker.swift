import Foundation

/// Tracks which cached resources have already been revalidated during this app
/// launch. Screens read from the cache on every appearance and only reach the
/// network the first time a key is claimed, so navigating back and forth never
/// costs a request.
///
/// Deliberately in-memory: "once per launch" has to reset on a cold start.
@MainActor
final class SessionRefreshTracker {
    private var claimed: Set<String> = []

    /// `true` the first time a key is requested this launch.
    func claim(_ key: String) -> Bool {
        claimed.insert(key).inserted
    }

    /// Lets a failed refresh be retried on the next appearance.
    func release(_ key: String) {
        claimed.remove(key)
    }

    func reset() {
        claimed.removeAll()
    }
}

enum RefreshKey {
    /// Conversations and folders are fetched together.
    static let conversations = "chat:conversations"
    static let chatModels = "chat:models"
    static let goals = "goals:all"
    static let profile = "profile"
    static let integrations = "settings:integrations"

    static func messages(_ conversationId: UUID) -> String {
        "chat:messages:\(conversationId.uuidString)"
    }

    static func pinnedKbit(_ kbitId: UUID) -> String {
        "chat:pinned-kbit:\(kbitId.uuidString)"
    }

    static func kbitDiscussion(_ kbitId: UUID) -> String {
        "kbit:discussion:\(kbitId.uuidString)"
    }

    static func diary(_ dateISO: String) -> String {
        "diary:\(dateISO)"
    }
}
