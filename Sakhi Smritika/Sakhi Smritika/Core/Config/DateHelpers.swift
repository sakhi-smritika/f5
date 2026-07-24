import Foundation

enum DateHelpers {
    /// Local calendar date as `yyyy-MM-dd`.
    static func todayISODate(calendar: Calendar = .current) -> String {
        string(from: Date(), calendar: calendar)
    }

    static func string(from date: Date, calendar: Calendar = .current) -> String {
        let components = calendar.dateComponents([.year, .month, .day], from: date)
        let year = components.year ?? 0
        let month = components.month ?? 0
        let day = components.day ?? 0
        return String(format: "%04d-%02d-%02d", year, month, day)
    }

    static func date(from iso: String, calendar: Calendar = .current) -> Date? {
        let parts = iso.split(separator: "-").compactMap { Int($0) }
        guard parts.count == 3 else { return nil }
        var components = DateComponents()
        components.year = parts[0]
        components.month = parts[1]
        components.day = parts[2]
        return calendar.date(from: components)
    }

    static func addDays(_ iso: String, delta: Int, calendar: Calendar = .current) -> String {
        guard let base = date(from: iso, calendar: calendar),
              let shifted = calendar.date(byAdding: .day, value: delta, to: base)
        else { return iso }
        return string(from: shifted, calendar: calendar)
    }

    static func isFuture(_ iso: String, calendar: Calendar = .current) -> Bool {
        iso > todayISODate(calendar: calendar)
    }

    static func displayLabel(_ iso: String, calendar: Calendar = .current) -> String {
        guard let date = date(from: iso, calendar: calendar) else { return iso }
        let formatter = DateFormatter()
        formatter.calendar = calendar
        formatter.locale = .current
        formatter.setLocalizedDateFormatFromTemplate("EEE MMM d, yyyy")
        return formatter.string(from: date)
    }
}
