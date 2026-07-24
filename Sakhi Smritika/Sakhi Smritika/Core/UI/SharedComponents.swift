import SwiftUI

enum SaveStatus: Equatable {
    case idle
    case saving
    case saved
    case error(String)

    var label: String {
        switch self {
        case .idle: return "Save"
        case .saving: return "Saving…"
        case .saved: return "Saved"
        case .error: return "Retry"
        }
    }

    static func == (lhs: SaveStatus, rhs: SaveStatus) -> Bool {
        switch (lhs, rhs) {
        case (.idle, .idle), (.saving, .saving), (.saved, .saved):
            return true
        case (.error(let a), .error(let b)):
            return a == b
        default:
            return false
        }
    }
}

struct SaveButton: View {
    let status: SaveStatus
    let action: () -> Void

    var body: some View {
        Button(action: action) {
            HStack(spacing: 8) {
                if status == .saving {
                    ProgressView()
                        .controlSize(.small)
                } else if status == .saved {
                    Image(systemName: "checkmark.circle.fill")
                }
                Text(status.label)
            }
            .frame(maxWidth: .infinity)
        }
        .buttonStyle(.borderedProminent)
        .disabled(status == .saving)
        .sensoryFeedback(.success, trigger: status == .saved)
    }
}

struct LoadingView: View {
    var message: String = "Loading…"

    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text(message)
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
    }
}

struct EmptyStateView: View {
    let systemImage: String
    let title: String
    var message: String? = nil

    var body: some View {
        ContentUnavailableView {
            Label(title, systemImage: systemImage)
        } description: {
            if let message {
                Text(message)
            }
        }
    }
}

struct FeaturePlaceholderView: View {
    let title: String
    let systemImage: String
    var subtitle: String = "Coming in the next phase"
    /// When `false`, caller owns the `NavigationStack` (e.g. pushed from More).
    var embedsNavigation: Bool = true

    var body: some View {
        Group {
            if embedsNavigation {
                NavigationStack { content }
            } else {
                content
            }
        }
    }

    private var content: some View {
        ContentUnavailableView {
            Label(title, systemImage: systemImage)
        } description: {
            Text(subtitle)
        }
        .navigationTitle(title)
    }
}
