import SwiftUI

struct ToolStepsView: View {
    let steps: [ToolStep]
    @State private var expanded = false

    private var current: ToolStep? {
        steps.first(where: { $0.status == .running }) ?? steps.last
    }

    var body: some View {
        if steps.isEmpty {
            EmptyView()
        } else if let current {
            VStack(alignment: .leading, spacing: 8) {
                Button {
                    expanded.toggle()
                } label: {
                    HStack(spacing: 8) {
                        Image(systemName: expanded ? "chevron.down" : "chevron.right")
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.secondary)

                        if current.status == .running {
                            ProgressView()
                                .controlSize(.mini)
                        } else {
                            Image(systemName: "wrench.and.screwdriver")
                                .font(.caption)
                                .foregroundStyle(.secondary)
                        }

                        Text(current.name)
                            .font(.caption.monospaced())
                            .foregroundStyle(.primary)
                            .lineLimit(1)

                        Text(current.status.rawValue)
                            .font(.caption2)
                            .foregroundStyle(statusColor(current.status))
                            .textCase(.lowercase)

                        if steps.count > 1 {
                            Text("\(steps.count) steps")
                                .font(.caption2)
                                .foregroundStyle(.tertiary)
                        }

                        Spacer(minLength: 0)
                    }
                    .padding(.horizontal, 10)
                    .padding(.vertical, 8)
                    .background(.quaternary.opacity(0.45), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                }
                .buttonStyle(.plain)

                if expanded {
                    VStack(alignment: .leading, spacing: 8) {
                        ForEach(steps) { step in
                            VStack(alignment: .leading, spacing: 6) {
                                HStack {
                                    Text(step.name)
                                        .font(.caption.monospaced())
                                    Spacer()
                                    Text(step.status.rawValue)
                                        .font(.caption2)
                                        .foregroundStyle(statusColor(step.status))
                                        .textCase(.lowercase)
                                }

                                Text(step.argsJSON)
                                    .font(.caption2.monospaced())
                                    .foregroundStyle(.secondary)
                                    .frame(maxWidth: .infinity, alignment: .leading)
                                    .padding(8)
                                    .background(Color(.secondarySystemBackground), in: RoundedRectangle(cornerRadius: 8, style: .continuous))
                            }
                            .padding(10)
                            .background(.quaternary.opacity(0.25), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
                        }
                    }
                }
            }
        }
    }

    private func statusColor(_ status: ToolStepStatus) -> Color {
        switch status {
        case .running:
            return .accentColor
        case .done:
            return .secondary
        case .error:
            return .orange
        }
    }
}
