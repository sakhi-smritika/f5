import Auth
import Foundation
import Observation

@MainActor
@Observable
final class DayLogViewModel {
    var dateISO = DateHelpers.todayISODate()
    var dayLog: [String: String]
    var loadError: String?
    var saveStatus: SaveStatus = .idle

    static let hours = Array(0..<24)

    private(set) var isRefreshing = false
    private(set) var hasData = false

    /// Only block the form with a spinner when there is nothing cached to show.
    var isLoading: Bool { isRefreshing && !hasData }

    /// Guards the editable hours: a background refresh must never overwrite text
    /// the user is in the middle of typing.
    private var hasUnsavedEdits = false

    private let authService: AuthService
    private let cache: CacheStore
    private let refreshTracker: SessionRefreshTracker

    init(authService: AuthService, cache: CacheStore, refreshTracker: SessionRefreshTracker) {
        self.authService = authService
        self.cache = cache
        self.refreshTracker = refreshTracker
        self.dayLog = DayLogViewModel.emptyLog()
        readFromCache()
    }

    static func emptyLog() -> [String: String] {
        Dictionary(uniqueKeysWithValues: hours.map { (String($0), "") })
    }

    static func hourLabel(_ hour: Int) -> String {
        String(format: "%02d:00 – %02d:00", hour, hour + 1)
    }

    func appear() async {
        guard !hasUnsavedEdits else { return }
        readFromCache()
        // Shares its key with the Diary screen: both read the same `diary` row, so
        // whichever opens first pays for the fetch.
        guard refreshTracker.claim(RefreshKey.diary(dateISO)) else { return }
        await refresh(date: dateISO)
    }

    /// Moving to another day discards the previous day's edit state.
    func dateChanged() async {
        hasUnsavedEdits = false
        saveStatus = .idle
        loadError = nil
        readFromCache()
        guard refreshTracker.claim(RefreshKey.diary(dateISO)) else { return }
        await refresh(date: dateISO)
    }

    private func readFromCache() {
        guard let cached = cache.diaryEntry(date: dateISO) else {
            dayLog = DayLogViewModel.emptyLog()
            hasData = false
            return
        }
        apply(cached.value)
        hasData = true
    }

    private func apply(_ entry: DiaryEntry?) {
        var next = DayLogViewModel.emptyLog()
        for (key, value) in entry?.dayLog ?? [:] {
            next[key] = value
        }
        dayLog = next
    }

    private func refresh(date: String) async {
        isRefreshing = true
        loadError = nil
        defer { isRefreshing = false }

        do {
            let entry = try await DiaryService.entry(for: date)
            cache.setDiaryEntry(entry, date: date)
            // Drop the result if the user changed day or started typing meanwhile.
            guard date == dateISO, !hasUnsavedEdits else { return }
            apply(entry)
            hasData = true
        } catch {
            refreshTracker.release(RefreshKey.diary(date))
            if !hasData {
                loadError = error.localizedDescription
            }
        }
    }

    func setHour(_ hour: Int, value: String) {
        dayLog[String(hour)] = value
        hasUnsavedEdits = true
        if saveStatus != .idle { saveStatus = .idle }
    }

    func save() async {
        guard let userId = authService.user?.id else {
            saveStatus = .error("You must be signed in to save.")
            return
        }

        let date = dateISO
        saveStatus = .saving
        do {
            let saved = try await DiaryService.saveDayLog(
                date: date,
                dayLog: dayLog,
                userId: userId
            )
            cache.setDiaryEntry(saved, date: date)
            guard date == dateISO else { return }
            apply(saved)
            hasData = true
            hasUnsavedEdits = false
            saveStatus = .saved
        } catch {
            saveStatus = .error(error.localizedDescription)
        }
    }
}
