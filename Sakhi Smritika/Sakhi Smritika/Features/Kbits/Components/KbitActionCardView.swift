import SwiftUI

struct KbitActionCardView: View {
    let isGenerating: Bool
    let isRefreshing: Bool
    let onInvoke: () -> Void
    let onRefresh: () -> Void
    let onBecameVisible: () -> Void

    var body: some View {
        VStack(spacing: 24) {
            VStack(spacing: 8) {
                Image(systemName: "sparkles")
                    .font(.largeTitle)
                    .foregroundStyle(.secondary)

                Text("You're caught up")
                    .font(.title2.weight(.semibold))

                Text(
                    isGenerating
                        ? "Generation is running on the server. Tap Refresh when ready, or wait for it to finish."
                        : "Generate new bits or refresh to load any that are ready."
                )
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .multilineTextAlignment(.center)
                .padding(.horizontal, 8)
            }

            VStack(spacing: 12) {
                Button(action: onInvoke) {
                    HStack(spacing: 8) {
                        if isGenerating {
                            ProgressView()
                                .controlSize(.small)
                        }
                        Text(isGenerating ? "Generating…" : "Invoke")
                            .font(.body.weight(.semibold))
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                }
                .buttonStyle(.borderedProminent)
                .disabled(isGenerating || isRefreshing)

                Button(action: onRefresh) {
                    HStack(spacing: 8) {
                        if isRefreshing {
                            ProgressView()
                                .controlSize(.small)
                        }
                        Text(isRefreshing ? "Refreshing…" : "Refresh")
                            .font(.body.weight(.semibold))
                    }
                    .frame(maxWidth: .infinity)
                    .padding(.vertical, 14)
                }
                .buttonStyle(.bordered)
                .disabled(isGenerating || isRefreshing)
            }
        }
        .padding(28)
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(
            Color(.secondarySystemGroupedBackground),
            in: RoundedRectangle(cornerRadius: 20, style: .continuous)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(Color.primary.opacity(0.12), lineWidth: 1)
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
        .onAppear(perform: onBecameVisible)
    }
}
