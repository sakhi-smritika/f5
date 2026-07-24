import SwiftUI

struct DateNavigator: View {
    @Binding var dateISO: String
    var allowsFuture: Bool = false

    private var canGoNext: Bool {
        allowsFuture || !DateHelpers.isFuture(DateHelpers.addDays(dateISO, delta: 1))
    }

    var body: some View {
        HStack(spacing: 12) {
            Button {
                dateISO = DateHelpers.addDays(dateISO, delta: -1)
            } label: {
                Image(systemName: "chevron.left")
                    .font(.body.weight(.semibold))
                    .frame(width: 36, height: 36)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)

            Text(DateHelpers.displayLabel(dateISO))
                .font(.headline)
                .frame(maxWidth: .infinity)

            Button {
                guard canGoNext else { return }
                dateISO = DateHelpers.addDays(dateISO, delta: 1)
            } label: {
                Image(systemName: "chevron.right")
                    .font(.body.weight(.semibold))
                    .frame(width: 36, height: 36)
                    .contentShape(Rectangle())
            }
            .buttonStyle(.plain)
            .disabled(!canGoNext)
            .opacity(canGoNext ? 1 : 0.35)
        }
        .padding(.horizontal, 4)
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Date \(DateHelpers.displayLabel(dateISO))")
    }
}
