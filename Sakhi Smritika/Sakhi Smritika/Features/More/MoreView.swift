import SwiftUI

struct MoreView: View {
    @Environment(AuthService.self) private var authService
    @State private var showSignOutConfirm = false
    @State private var path = NavigationPath()

    private enum Destination: Hashable {
        case profile
        case goals
        case settings
    }

    var body: some View {
        NavigationStack(path: $path) {
            ScrollView {
                VStack(spacing: 36) {
                    moreIconButton(
                        systemImage: "person.crop.circle",
                        label: "Profile"
                    ) {
                        path.append(Destination.profile)
                    }

                    moreIconButton(
                        systemImage: "target",
                        label: "Goals"
                    ) {
                        path.append(Destination.goals)
                    }

                    moreIconButton(
                        systemImage: "gearshape",
                        label: "Settings"
                    ) {
                        path.append(Destination.settings)
                    }

                    Divider()
                        .frame(width: 48)
                        .padding(.vertical, 4)

                    moreIconButton(
                        systemImage: "rectangle.portrait.and.arrow.right",
                        label: "Log out",
                        tint: .red
                    ) {
                        showSignOutConfirm = true
                    }
                }
                .frame(maxWidth: .infinity)
                .padding(.top, 48)
                .padding(.bottom, 32)
            }
            .navigationTitle("More")
            .navigationDestination(for: Destination.self) { destination in
                switch destination {
                case .profile:
                    ProfileView()
                case .goals:
                    GoalsListView()
                case .settings:
                    SettingsView()
                }
            }
            .confirmationDialog(
                "Sign out of Sakhi Smritika?",
                isPresented: $showSignOutConfirm,
                titleVisibility: .visible
            ) {
                Button("Log Out", role: .destructive) {
                    Task { await authService.signOut() }
                }
                Button("Cancel", role: .cancel) {}
            }
        }
    }

    private func moreIconButton(
        systemImage: String,
        label: String,
        tint: Color = .primary,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 34, weight: .regular))
                .foregroundStyle(tint)
                .frame(width: 64, height: 64)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}
