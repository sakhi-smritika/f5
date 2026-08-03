import Auth
import Foundation
import Observation

struct EditableNutritionEntry: Identifiable, Hashable {
    let id: UUID
    var hour: Int
    var food: String

    init(id: UUID = UUID(), hour: Int, food: String) {
        self.id = id
        self.hour = hour
        self.food = food
    }

    var asNutritionEntry: NutritionEntry {
        NutritionEntry(hour: hour, food: food)
    }

    static func from(_ entry: NutritionEntry) -> EditableNutritionEntry {
        EditableNutritionEntry(hour: entry.hour, food: entry.food)
    }
}

@MainActor
@Observable
final class DayLogViewModel {
    var dateISO = DateHelpers.todayISODate()
    var dayLog: [String: String]
    var nutritionEntries: [EditableNutritionEntry] = []
    var activeTemplates: [NutritionTemplate] = []
    var hourGroups = HourGroupPreferencesStore.shared.load()

    var isHoursOpen = false
    var isNutritionOpen = false

    var loadError: String?
    var saveStatus: SaveStatus = .idle
    var templateSaveError: String?

    var editingNutritionEntry: EditableNutritionEntry?
    var isAddingNutritionEntry = false
    var draftHour = Calendar.current.component(.hour, from: Date())
    var draftFood = ""

    static let hours = Array(0..<24)

    private(set) var isRefreshing = false
    private(set) var hasData = false

    var isLoading: Bool { isRefreshing && !hasData }

    private var hasUnsavedEdits = false

    /// Last persisted hour log — used when a template swipe saves nutrition only.
    private var persistedDayLog = DayLogViewModel.emptyLog()

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

    var sortedNutritionEntries: [EditableNutritionEntry] {
        nutritionEntries.sorted { lhs, rhs in
            if lhs.hour != rhs.hour { return lhs.hour < rhs.hour }
            return lhs.food.localizedCaseInsensitiveCompare(rhs.food) == .orderedAscending
        }
    }

    func swipableTemplates() -> [NutritionTemplate] {
        activeTemplates.filter { template in
            !nutritionEntries.contains {
                $0.hour == template.hour &&
                $0.food.trimmingCharacters(in: .whitespacesAndNewlines) ==
                template.nutrition.trimmingCharacters(in: .whitespacesAndNewlines)
            }
        }
    }

    func appear() async {
        hourGroups = HourGroupPreferencesStore.shared.load()
        guard !hasUnsavedEdits else { return }
        readFromCache()
        guard refreshTracker.claim(RefreshKey.diary(dateISO)) else { return }
        await refresh(date: dateISO)
        await loadTemplates()
    }

    func dateChanged() async {
        hasUnsavedEdits = false
        saveStatus = .idle
        templateSaveError = nil
        loadError = nil
        readFromCache()
        guard refreshTracker.claim(RefreshKey.diary(dateISO)) else { return }
        await refresh(date: dateISO)
        await loadTemplates()
    }

    func reloadHourGroups() {
        hourGroups = HourGroupPreferencesStore.shared.load()
    }

    private func readFromCache() {
        guard let cached = cache.diaryEntry(date: dateISO) else {
            dayLog = DayLogViewModel.emptyLog()
            nutritionEntries = []
            hasData = false
            return
        }
        apply(cached.value)
        hasData = true
    }

    private func apply(_ entry: DiaryEntry?, preserveHourEdits: Bool = false) {
        if !preserveHourEdits || !hasUnsavedEdits {
            var next = DayLogViewModel.emptyLog()
            for (key, value) in entry?.dayLog ?? [:] {
                next[key] = value
            }
            dayLog = next
            persistedDayLog = next
        }
        nutritionEntries = (entry?.nutritionEntries ?? []).map(EditableNutritionEntry.from)
    }

    private func refresh(date: String) async {
        isRefreshing = true
        loadError = nil
        defer { isRefreshing = false }

        do {
            let entry = try await DiaryService.entry(for: date)
            cache.setDiaryEntry(entry, date: date)
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

    private func loadTemplates() async {
        do {
            activeTemplates = try await NutritionTemplateService.listActive()
        } catch {
            templateSaveError = error.localizedDescription
        }
    }

    func setHour(_ hour: Int, value: String) {
        dayLog[String(hour)] = value
        markEdited()
    }

    func beginAddNutritionEntry() {
        draftHour = Calendar.current.component(.hour, from: Date())
        draftFood = ""
        isAddingNutritionEntry = true
    }

    func beginEditNutritionEntry(_ entry: EditableNutritionEntry) {
        editingNutritionEntry = entry
        draftHour = entry.hour
        draftFood = entry.food
    }

    func commitDraftNutritionEntry() {
        let food = draftFood.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !food.isEmpty else { return }

        if let editing = editingNutritionEntry,
           let index = nutritionEntries.firstIndex(where: { $0.id == editing.id }) {
            nutritionEntries[index].hour = draftHour
            nutritionEntries[index].food = food
        } else {
            nutritionEntries.append(EditableNutritionEntry(hour: draftHour, food: food))
        }

        editingNutritionEntry = nil
        isAddingNutritionEntry = false
        markEdited()
    }

    func cancelDraftNutritionEntry() {
        editingNutritionEntry = nil
        isAddingNutritionEntry = false
    }

    func deleteNutritionEntry(_ entry: EditableNutritionEntry) {
        nutritionEntries.removeAll { $0.id == entry.id }
        markEdited()
    }

    func addFromTemplate(_ template: NutritionTemplate) async {
        let entry = EditableNutritionEntry(hour: template.hour, food: template.nutrition)
        nutritionEntries.append(entry)
        await persist(dayLog: persistedDayLog, clearEditsOnSuccess: false)
    }

    func save() async {
        await persist(dayLog: dayLog, clearEditsOnSuccess: true)
    }

    private func persist(dayLog dayLogToSave: [String: String], clearEditsOnSuccess: Bool) async {
        guard let userId = authService.user?.id else {
            saveStatus = .error("You must be signed in to save.")
            return
        }

        let date = dateISO
        saveStatus = .saving
        templateSaveError = nil

        do {
            let saved = try await DiaryService.saveDayLog(
                date: date,
                dayLog: dayLogToSave,
                nutritionEntries: nutritionEntries.map(\.asNutritionEntry),
                userId: userId
            )
            cache.setDiaryEntry(saved, date: date)
            guard date == dateISO else { return }
            apply(saved, preserveHourEdits: !clearEditsOnSuccess)
            hasData = true
            if clearEditsOnSuccess {
                hasUnsavedEdits = false
            }
            saveStatus = .saved
        } catch {
            saveStatus = .error(error.localizedDescription)
            templateSaveError = error.localizedDescription
        }
    }

    private func markEdited() {
        hasUnsavedEdits = true
        if saveStatus != .idle { saveStatus = .idle }
    }
}
