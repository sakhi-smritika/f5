import SwiftUI

enum MoreDestination: String, Identifiable {
    case profile
    case goals
    case settings

    var id: String { rawValue }
}

/// Root of the More tab: entry points for the secondary screens plus sign out.
struct MoreView: View {
    let onSignOut: () -> Void

    var body: some View {
        NavigationStack {
            List {
                Section {
                    row(.profile, systemImage: "person.crop.circle", label: "Profile")
                    row(.goals, systemImage: "target", label: "Goals")
                    row(.settings, systemImage: "gearshape", label: "Settings")
                }

                Section {
                    Button(role: .destructive, action: onSignOut) {
                        Label("Log out", systemImage: "rectangle.portrait.and.arrow.right")
                    }
                }
            }
            .navigationTitle("More")
            .navigationDestination(for: MoreDestination.self) { destination in
                switch destination {
                case .profile:
                    ProfileView()
                case .goals:
                    GoalsListView()
                case .settings:
                    SettingsView()
                }
            }
        }
    }

    private func row(
        _ destination: MoreDestination,
        systemImage: String,
        label: String
    ) -> some View {
        NavigationLink(value: destination) {
            Label(label, systemImage: systemImage)
        }
    }
}
