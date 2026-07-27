import Observation
import SwiftUI

/// App-wide dependencies. Injected once at the root.
@MainActor
@Observable
final class AppDependencies {
    let authService: AuthService
    let apiClient: APIClient
    let cache: CacheStore
    let refreshTracker: SessionRefreshTracker
    let threadRegistry: ChatThreadRegistry

    init() {
        let auth = AuthService()
        let cache = CacheStore()
        let refreshTracker = SessionRefreshTracker()
        let threadRegistry = ChatThreadRegistry()

        self.authService = auth
        self.apiClient = APIClient(authService: auth)
        self.cache = cache
        self.refreshTracker = refreshTracker
        self.threadRegistry = threadRegistry

        // An explicit log out should leave nothing of the previous user behind.
        auth.onExplicitSignOut = {
            cache.clearAll()
            refreshTracker.reset()
            threadRegistry.removeAll()
        }
    }

    /// Drops a cache belonging to a different account, and gives the new session
    /// a clean slate to revalidate against.
    func prepareCache(for userId: UUID) {
        cache.ensureOwner(userId: userId)
    }
}
