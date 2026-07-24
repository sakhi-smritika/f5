import Auth
import Foundation
import Observation

@MainActor
@Observable
final class ProfileViewModel {
    var fullName = ""
    var userInformation = ""
    var systemInstructions = ""
    var isLoading = true
    var loadError: String?
    var saveStatus: SaveStatus = .idle

    private let authService: AuthService

    init(authService: AuthService) {
        self.authService = authService
    }

    func load() async {
        guard let userId = authService.user?.id else {
            isLoading = false
            loadError = "You must be signed in."
            return
        }

        isLoading = true
        loadError = nil
        defer { isLoading = false }

        do {
            let profile = try await ProfileService.profile(userId: userId)
            fullName = profile?.fullName ?? ""
            userInformation = profile?.userInformation ?? ""
            systemInstructions = profile?.systemInstructions ?? ""
        } catch {
            loadError = error.localizedDescription
        }
    }

    func markEdited() {
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
            fullName = saved.fullName ?? ""
            userInformation = saved.userInformation ?? ""
            systemInstructions = saved.systemInstructions ?? ""
            saveStatus = .saved
        } catch {
            saveStatus = .error(error.localizedDescription)
        }
    }
}
