import Auth
import Foundation
import Observation

@MainActor
@Observable
final class ProfileViewModel {
    var fullName = ""
    var userInformation = ""
    var systemInstructions = ""
    var loadError: String?
    var saveStatus: SaveStatus = .idle

    private(set) var isRefreshing = false
    private(set) var hasData = false

    /// Only block the form with a spinner when there is nothing cached to show.
    var isLoading: Bool { isRefreshing && !hasData }

    /// Guards the editable fields: a background refresh must never overwrite text
    /// the user is in the middle of typing.
    private var hasUnsavedEdits = false

    private let authService: AuthService
    private let cache: CacheStore
    private let refreshTracker: SessionRefreshTracker

    init(authService: AuthService, cache: CacheStore, refreshTracker: SessionRefreshTracker) {
        self.authService = authService
        self.cache = cache
        self.refreshTracker = refreshTracker
        readFromCache()
    }

    func appear() async {
        guard !hasUnsavedEdits else { return }
        readFromCache()
        guard refreshTracker.claim(RefreshKey.profile) else { return }
        await refresh()
    }

    private func readFromCache() {
        guard let userId = authService.user?.id,
              let cached = cache.profile(userId: userId) else { return }
        apply(cached.value)
        hasData = true
    }

    private func apply(_ profile: Profile?) {
        fullName = profile?.fullName ?? ""
        userInformation = profile?.userInformation ?? ""
        systemInstructions = profile?.systemInstructions ?? ""
    }

    private func refresh() async {
        guard let userId = authService.user?.id else {
            loadError = "You must be signed in."
            return
        }

        isRefreshing = true
        loadError = nil
        defer { isRefreshing = false }

        do {
            let profile = try await ProfileService.profile(userId: userId)
            cache.setProfile(profile, userId: userId)
            guard !hasUnsavedEdits else { return }
            apply(profile)
            hasData = true
        } catch {
            refreshTracker.release(RefreshKey.profile)
            if !hasData {
                loadError = error.localizedDescription
            }
        }
    }

    func markEdited() {
        hasUnsavedEdits = true
        if saveStatus != .idle { saveStatus = .idle }
    }

    func save() async {
        guard let userId = authService.user?.id else {
            saveStatus = .error("You must be signed in to save.")
            return
        }

        saveStatus = .saving
        do {
            let saved = try await ProfileService.update(
                userId: userId,
                fullName: fullName,
                userInformation: userInformation,
                systemInstructions: systemInstructions
            )
            apply(saved)
            cache.setProfile(saved, userId: userId)
            hasData = true
            hasUnsavedEdits = false
            saveStatus = .saved
        } catch {
            saveStatus = .error(error.localizedDescription)
        }
    }
}
