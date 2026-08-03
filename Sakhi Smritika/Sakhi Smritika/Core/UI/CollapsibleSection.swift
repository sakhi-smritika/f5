import SwiftUI

struct CollapsibleSection<Content: View>: View {
    let title: String
    @Binding var isOpen: Bool
    @ViewBuilder let content: () -> Content

    var body: some View {
        VStack(alignment: .leading, spacing: 10) {
            Button {
                withAnimation(.snappy) { isOpen.toggle() }
            } label: {
                HStack {
                    Text(title)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                    Spacer()
                    Image(systemName: "chevron.down")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                        .rotationEffect(.degrees(isOpen ? 0 : -90))
                }
            }
            .buttonStyle(.plain)

            if isOpen {
                content()
            }
        }
        .padding(16)
        .background(
            Color(.secondarySystemGroupedBackground),
            in: RoundedRectangle(cornerRadius: 18, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .strokeBorder(Color.primary.opacity(0.12), lineWidth: 1)
        )
    }
}
