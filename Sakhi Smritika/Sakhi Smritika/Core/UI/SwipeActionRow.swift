import SwiftUI

/// Swipe row for use inside `ScrollView` where `swipeActions` is unavailable.
struct SwipeActionRow<Content: View>: View {
    struct Action {
        let title: String
        let systemImage: String
        let tint: Color
        let handler: () -> Void

        init(
            title: String,
            systemImage: String,
            tint: Color,
            handler: @escaping () -> Void
        ) {
            self.title = title
            self.systemImage = systemImage
            self.tint = tint
            self.handler = handler
        }
    }

    let leading: Action?
    let trailing: Action?
    var onTap: (() -> Void)?
    @ViewBuilder let content: () -> Content

    @State private var offset: CGFloat = 0
    @State private var suppressNextTap = false

    private let actionWidth: CGFloat = 88
    private let triggerThreshold: CGFloat = 64

    init(
        leading: Action? = nil,
        trailing: Action? = nil,
        onTap: (() -> Void)? = nil,
        @ViewBuilder content: @escaping () -> Content
    ) {
        self.leading = leading
        self.trailing = trailing
        self.onTap = onTap
        self.content = content
    }

    var body: some View {
        ZStack(alignment: .leading) {
            HStack(spacing: 0) {
                if let leading {
                    actionView(leading)
                        .frame(width: actionWidth)
                }
                Spacer(minLength: 0)
                if let trailing {
                    actionView(trailing)
                        .frame(width: actionWidth)
                }
            }

            content()
                .frame(maxWidth: .infinity, alignment: .leading)
                .background {
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(Color(.secondarySystemGroupedBackground))
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .fill(Color(.tertiarySystemFill))
                }
                .overlay(
                    RoundedRectangle(cornerRadius: 14, style: .continuous)
                        .strokeBorder(Color.primary.opacity(0.08), lineWidth: 1)
                )
                .offset(x: offset)
                .contentShape(Rectangle())
                .onTapGesture {
                    guard !suppressNextTap else {
                        suppressNextTap = false
                        return
                    }
                    onTap?()
                }
                .highPriorityGesture(dragGesture)
        }
        .clipShape(RoundedRectangle(cornerRadius: 14, style: .continuous))
    }

    private var dragGesture: some Gesture {
        DragGesture(minimumDistance: 12, coordinateSpace: .local)
            .onChanged { value in
                let horizontal = value.translation.width
                let vertical = value.translation.height
                guard abs(horizontal) > abs(vertical) else { return }

                if horizontal > 0, leading != nil {
                    offset = min(horizontal, actionWidth)
                } else if horizontal < 0, trailing != nil {
                    offset = max(horizontal, -actionWidth)
                }
            }
            .onEnded { value in
                let horizontal = value.translation.width
                let vertical = value.translation.height
                guard abs(horizontal) > abs(vertical) else {
                    withAnimation(.snappy) { offset = 0 }
                    return
                }

                if horizontal > triggerThreshold, let leading {
                    suppressNextTap = true
                    leading.handler()
                } else if horizontal < -triggerThreshold, let trailing {
                    suppressNextTap = true
                    trailing.handler()
                }

                withAnimation(.snappy) { offset = 0 }
            }
    }

    private func actionView(_ action: Action) -> some View {
        Button(action: action.handler) {
            VStack(spacing: 4) {
                Image(systemName: action.systemImage)
                Text(action.title)
                    .font(.caption2.weight(.semibold))
            }
            .frame(maxWidth: .infinity, maxHeight: .infinity)
            .foregroundStyle(.white)
            .background(action.tint)
        }
        .buttonStyle(.plain)
    }
}
