import Auth
import Foundation
import Observation

@MainActor
@Observable
final class DiaryViewModel {
    var dateISO = DateHelpers.todayISODate()
    var howWasTheDay = ""
    var majorEvents = ""
    var generalContent = ""
    var isLoading = false
    var loadError: String?
    var saveStatus: SaveStatus = .idle

    var isHowOpen = true
    var isMajorOpen = true
    var isGeneralOpen = true

    private let authService: AuthService

    init(authService: AuthService) {
        self.authService = authService
    }

    func load() async {
        isLoading = true
        loadError = nil
        saveStatus = .idle
        defer { isLoading = false }

        do {
            let entry = try await DiaryService.entry(for: dateISO)
            howWasTheDay = entry?.howWasTheDay ?? ""
            majorEvents = entry?.majorEvents ?? ""
            generalContent = entry?.generalContent ?? ""
        } catch {
            howWasTheDay = ""
            majorEvents = ""
            generalContent = ""
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
            let saved = try await DiaryService.saveDiary(
                date: dateISO,
                howWasTheDay: howWasTheDay,
                majorEvents: majorEvents,
                generalContent: generalContent,
                userId: userId
            )
            howWasTheDay = saved.howWasTheDay ?? ""
            majorEvents = saved.majorEvents ?? ""
            generalContent = saved.generalContent ?? ""
            saveStatus = .saved
        } catch {
            saveStatus = .error(error.localizedDescription)
        }
    }
}
