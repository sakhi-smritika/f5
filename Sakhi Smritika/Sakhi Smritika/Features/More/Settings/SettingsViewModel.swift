import Foundation
import Observation

@MainActor
@Observable
final class SettingsViewModel {
    private let apiClient: APIClient
    private let oauthPresenter = GoogleOAuthPresenter()

    var status: GoogleConnectionStatus?
    var isLoading = false
    var isBusy = false
    var loadError: String?
    var actionError: String?
    var flashMessage: String?

    init(apiClient: APIClient) {
        self.apiClient = apiClient
    }

    var isConnected: Bool {
        status?.connected ?? false
    }

    func load() async {
        isLoading = true
        loadError = nil
        defer { isLoading = false }

        do {
            status = try await IntegrationsService.googleStatus(api: apiClient)
        } catch {
            loadError = error.localizedDescription
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
            status = try await IntegrationsService.googleStatus(api: apiClient)
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
            status = GoogleConnectionStatus(connected: false, googleEmail: nil, connectedAt: nil)
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
