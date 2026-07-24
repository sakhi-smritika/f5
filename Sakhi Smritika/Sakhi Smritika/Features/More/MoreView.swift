import SwiftUI

enum MoreDestination: String, Identifiable {
    case profile
    case goals
    case settings

    var id: String { rawValue }
}

/// Compact icon stack matching the web settings / introspection flyout.
struct MoreMenuView: View {
    let onSelect: (MoreDestination) -> Void
    let onSignOut: () -> Void

    private let iconSize: CGFloat = 40

    var body: some View {
        VStack(spacing: 4) {
            moreIconButton(systemImage: "person.crop.circle", label: "Profile") {
                onSelect(.profile)
            }
            moreIconButton(systemImage: "target", label: "Goals") {
                onSelect(.goals)
            }
            moreIconButton(systemImage: "gearshape", label: "Settings") {
                onSelect(.settings)
            }

            Rectangle()
                .fill(.separator.opacity(0.5))
                .frame(width: iconSize - 12, height: 1)
                .padding(.vertical, 2)

            moreIconButton(
                systemImage: "rectangle.portrait.and.arrow.right",
                label: "Log out",
                tint: .red,
                action: onSignOut
            )
        }
        .padding(4)
        .frame(width: iconSize + 8)
        .fixedSize()
        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 12, style: .continuous)
                .strokeBorder(.separator.opacity(0.5), lineWidth: 1)
        )
        .shadow(color: .black.opacity(0.12), radius: 12, y: 4)
    }

    private func moreIconButton(
        systemImage: String,
        label: String,
        tint: Color = .primary,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.system(size: 18, weight: .regular))
                .foregroundStyle(tint)
                .frame(width: iconSize, height: iconSize)
                .contentShape(Rectangle())
        }
        .buttonStyle(.plain)
        .accessibilityLabel(label)
    }
}
