import Foundation
import Observation

@MainActor
@Observable
final class SettingsViewModel {
    private let apiClient: APIClient
    private let cache: CacheStore
    private let refreshTracker: SessionRefreshTracker
    private let oauthPresenter = GoogleOAuthPresenter()

    var status: GoogleConnectionStatus?
    var isBusy = false
    var loadError: String?
    var actionError: String?
    var flashMessage: String?

    private(set) var isRefreshing = false

    /// Only show the placeholder spinner when there is nothing cached to show.
    var isLoading: Bool { isRefreshing && status == nil }

    init(apiClient: APIClient, cache: CacheStore, refreshTracker: SessionRefreshTracker) {
        self.apiClient = apiClient
        self.cache = cache
        self.refreshTracker = refreshTracker
        status = cache.googleStatus()
    }

    var isConnected: Bool {
        status?.connected ?? false
    }

    func appear() async {
        if status == nil {
            status = cache.googleStatus()
        }
        guard refreshTracker.claim(RefreshKey.integrations) else { return }
        await refresh()
    }

    /// Pull to refresh always goes to the network.
    func reload() async {
        _ = refreshTracker.claim(RefreshKey.integrations)
        await refresh()
    }

    private func refresh() async {
        isRefreshing = true
        loadError = nil
        defer { isRefreshing = false }

        do {
            let loaded = try await IntegrationsService.googleStatus(api: apiClient)
            status = loaded
            cache.setGoogleStatus(loaded)
        } catch {
            refreshTracker.release(RefreshKey.integrations)
            if status == nil {
                loadError = error.localizedDescription
            }
        }
    }

    func toggleGoogle() async {
        if isConnected {
            await disconnect()
        } else {
            await connect()
        }
    }

    private func connect() async {
        isBusy = true
        actionError = nil
        flashMessage = nil
        defer { isBusy = false }

        do {
            let authorizeURL = try await IntegrationsService.googleAuthorizeURL(
                api: apiClient,
                successRedirect: AppConfig.oauthSuccessRedirect
            )
            let callbackURL = try await oauthPresenter.authenticate(
                url: authorizeURL,
                callbackScheme: AppConfig.oauthCallbackScheme
            )
            handleOAuthCallback(callbackURL)
            if actionError != nil {
                return
            }
            let loaded = try await IntegrationsService.googleStatus(api: apiClient)
            status = loaded
            cache.setGoogleStatus(loaded)
        } catch is CancellationError {
            // User dismissed the sheet — no error.
        } catch {
            actionError = error.localizedDescription
        }
    }

    private func disconnect() async {
        isBusy = true
        actionError = nil
        flashMessage = nil
        defer { isBusy = false }

        do {
            try await IntegrationsService.disconnectGoogle(api: apiClient)
            let disconnected = GoogleConnectionStatus(connected: false, googleEmail: nil, connectedAt: nil)
            status = disconnected
            cache.setGoogleStatus(disconnected)
            flashMessage = "Google disconnected."
        } catch {
            actionError = error.localizedDescription
        }
    }

    private func handleOAuthCallback(_ url: URL) {
        let items = URLComponents(url: url, resolvingAgainstBaseURL: false)?.queryItems ?? []
        let google = items.first { $0.name == "google" }?.value
        let message = items.first { $0.name == "message" }?.value

        if google == "connected" {
            flashMessage = "Google connected successfully."
        } else if google == "error" {
            actionError = message.map { "Google connection failed: \($0)" }
                ?? "Google connection failed."
        }
    }
}
