import Foundation

enum DayLogPeriod: String, CaseIterable, Identifiable, Codable {
    case morning
    case afternoon
    case evening
    case night

    var id: String { rawValue }

    var title: String {
        switch self {
        case .morning: return "Morning"
        case .afternoon: return "Afternoon"
        case .evening: return "Evening"
        case .night: return "Night"
        }
    }
}

struct HourRange: Codable, Hashable, Sendable {
    var start: Int
    var end: Int

    func contains(_ hour: Int) -> Bool {
        if start <= end {
            return hour >= start && hour <= end
        }
        return hour >= start || hour <= end
    }

    var label: String {
        String(format: "%02d:00 – %02d:59", start, end)
    }
}

struct DayLogHourGroups: Codable, Hashable, Sendable {
    var morning: HourRange
    var afternoon: HourRange
    var evening: HourRange
    var night: HourRange

    static let defaults = DayLogHourGroups(
        morning: HourRange(start: 6, end: 11),
        afternoon: HourRange(start: 12, end: 16),
        evening: HourRange(start: 17, end: 20),
        night: HourRange(start: 21, end: 5)
    )

    func range(for period: DayLogPeriod) -> HourRange {
        switch period {
        case .morning: return morning
        case .afternoon: return afternoon
        case .evening: return evening
        case .night: return night
        }
    }

    mutating func setRange(_ range: HourRange, for period: DayLogPeriod) {
        switch period {
        case .morning: morning = range
        case .afternoon: afternoon = range
        case .evening: evening = range
        case .night: night = range
        }
    }

    func period(for hour: Int) -> DayLogPeriod {
        for period in DayLogPeriod.allCases where range(for: period).contains(hour) {
            return period
        }
        return .morning
    }

    func hours(for period: DayLogPeriod) -> [Int] {
        (0..<24).filter { self.period(for: $0) == period }
    }
}

/// Persists day-log hour group ranges locally on device.
final class HourGroupPreferencesStore: Sendable {
    static let shared = HourGroupPreferencesStore()

    private let defaults: UserDefaults
    private let storageKey = "daylog.hourGroups"

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    func load() -> DayLogHourGroups {
        guard
            let data = defaults.data(forKey: storageKey),
            let groups = try? JSONDecoder().decode(DayLogHourGroups.self, from: data)
        else {
            return .defaults
        }
        return groups
    }

    func save(_ groups: DayLogHourGroups) {
        guard let data = try? JSONEncoder().encode(groups) else { return }
        defaults.set(data, forKey: storageKey)
    }
}
