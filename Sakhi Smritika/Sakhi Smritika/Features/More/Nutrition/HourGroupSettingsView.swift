import SwiftUI

struct HourGroupSettingsView: View {
    @State private var groups = HourGroupPreferencesStore.shared.load()

    var body: some View {
        Form {
            Section {
                Text("Choose which hours belong to each part of the day. These groupings appear in the Day Log Hours section and stay on this device.")
                    .font(.footnote)
                    .foregroundStyle(.secondary)
            }

            ForEach(DayLogPeriod.allCases) { period in
                Section(period.title) {
                    hourPicker(title: "Start", hour: startHourBinding(for: period))
                    hourPicker(title: "End", hour: endHourBinding(for: period))
                    Text("Covers: \(groups.range(for: period).label)")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }

            Section {
                Button("Reset to defaults") {
                    groups = .defaults
                    HourGroupPreferencesStore.shared.save(groups)
                }
            }
        }
        .navigationTitle("Hour Groups")
        .navigationBarTitleDisplayMode(.inline)
        .onChange(of: groups) { _, newValue in
            HourGroupPreferencesStore.shared.save(newValue)
        }
    }

    private func startHourBinding(for period: DayLogPeriod) -> Binding<Int> {
        Binding(
            get: { groups.range(for: period).start },
            set: { newValue in
                var range = groups.range(for: period)
                range.start = newValue
                groups.setRange(range, for: period)
            }
        )
    }

    private func endHourBinding(for period: DayLogPeriod) -> Binding<Int> {
        Binding(
            get: { groups.range(for: period).end },
            set: { newValue in
                var range = groups.range(for: period)
                range.end = newValue
                groups.setRange(range, for: period)
            }
        )
    }

    private func hourPicker(title: String, hour: Binding<Int>) -> some View {
        Picker(title, selection: hour) {
            ForEach(0..<24, id: \.self) { value in
                Text(String(format: "%02d:00", value)).tag(value)
            }
        }
    }
}
