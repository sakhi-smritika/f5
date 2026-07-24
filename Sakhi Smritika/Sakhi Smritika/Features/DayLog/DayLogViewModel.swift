import Auth
import Foundation
import Observation

@MainActor
@Observable
final class DayLogViewModel {
    var dateISO = DateHelpers.todayISODate()
    var dayLog: [String: String]
    var isLoading = false
    var loadError: String?
    var saveStatus: SaveStatus = .idle

    static let hours = Array(0..<24)

    private let authService: AuthService

    init(authService: AuthService) {
        self.authService = authService
        self.dayLog = DayLogViewModel.emptyLog()
    }

    static func emptyLog() -> [String: String] {
        Dictionary(uniqueKeysWithValues: hours.map { (String($0), "") })
    }

    static func hourLabel(_ hour: Int) -> String {
        String(format: "%02d:00 – %02d:00", hour, hour + 1)
    }

    func load() async {
        isLoading = true
        loadError = nil
        saveStatus = .idle
        defer { isLoading = false }

        do {
            let entry = try await DiaryService.entry(for: dateISO)
            var next = DayLogViewModel.emptyLog()
            if let stored = entry?.dayLog {
                for (key, value) in stored {
                    next[key] = value
                }
            }
            dayLog = next
        } catch {
            dayLog = DayLogViewModel.emptyLog()
            loadError = error.localizedDescription
        }
    }

    func setHour(_ hour: Int, value: String) {
        dayLog[String(hour)] = value
        if saveStatus != .idle { saveStatus = .idle }
    }

    func save() async {
        guard let userId = authService.user?.id else {
            saveStatus = .error("You must be signed in to save.")
            return
        }

        saveStatus = .saving
        do {
            let saved = try await DiaryService.saveDayLog(
                date: dateISO,
                dayLog: dayLog,
                userId: userId
            )
            var next = DayLogViewModel.emptyLog()
            if let stored = saved.dayLog {
                for (key, value) in stored {
                    next[key] = value
                }
            }
            dayLog = next
            saveStatus = .saved
        } catch {
            saveStatus = .error(error.localizedDescription)
        }
    }
}
