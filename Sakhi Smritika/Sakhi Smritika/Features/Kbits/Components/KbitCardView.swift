import SwiftUI

struct KbitCardView: View {
    let bit: KnowledgeBit
    let hasDiscussion: Bool
    let onLike: () -> Void
    let onDislike: () -> Void
    let onRelevant: () -> Void
    let onIrrelevant: () -> Void
    let onDiscuss: () -> Void
    let onDelete: () -> Void
    let onBecameVisible: () -> Void

    var body: some View {
        GeometryReader { geo in
            cardContent(in: geo.size)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)
                .frame(width: geo.size.width, height: geo.size.height)
                .onAppear(perform: onBecameVisible)
        }
    }

    private func cardContent(in size: CGSize) -> some View {
        ZStack(alignment: .bottom) {
            ScrollView {
                VStack(alignment: .leading, spacing: 16) {
                    HStack {
                        if !bit.isViewed {
                            Text("NEW")
                                .font(.caption2.weight(.bold))
                                .padding(.horizontal, 8)
                                .padding(.vertical, 4)
                                .background(Color.accentColor.opacity(0.2), in: Capsule())
                        }
                        Spacer()
                    }

                    Text(bit.title)
                        .font(.title2.weight(.semibold))
                        .frame(maxWidth: .infinity, alignment: .leading)

                    Text(bit.content)
                        .font(.body)
                        .foregroundStyle(.primary)
                        .frame(maxWidth: .infinity, alignment: .leading)
                        .textSelection(.enabled)

                    Spacer(minLength: 88)
                }
                .padding(20)
                .frame(minHeight: size.height - 20)
            }
            .scrollIndicators(.hidden)

            actionBar
                .padding(.horizontal, 16)
                .padding(.bottom, 16)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .background(
            Color(.secondarySystemGroupedBackground),
            in: RoundedRectangle(cornerRadius: 20, style: .continuous)
        )
        .overlay {
            RoundedRectangle(cornerRadius: 20, style: .continuous)
                .strokeBorder(Color.primary.opacity(0.12), lineWidth: 1)
        }
        .clipShape(RoundedRectangle(cornerRadius: 20, style: .continuous))
    }

    private var actionBar: some View {
        HStack(spacing: 18) {
            actionButton(
                systemImage: bit.isLiked ? "hand.thumbsup.fill" : "hand.thumbsup",
                tint: bit.isLiked ? .accentColor : .primary,
                action: onLike
            )
            actionButton(
                systemImage: bit.isDisliked ? "hand.thumbsdown.fill" : "hand.thumbsdown",
                tint: bit.isDisliked ? .orange : .primary,
                action: onDislike
            )
            actionButton(
                systemImage: bit.isMarkedRelavant ? "checkmark.circle.fill" : "checkmark.circle",
                tint: bit.isMarkedRelavant ? .green : .primary,
                action: onRelevant
            )
            actionButton(
                systemImage: bit.isMarkedIrrelavant ? "xmark.circle.fill" : "xmark.circle",
                tint: bit.isMarkedIrrelavant ? .red : .primary,
                action: onIrrelevant
            )

            Button(action: onDiscuss) {
                ZStack(alignment: .topTrailing) {
                    Image(systemName: "bubble.left")
                        .font(.title3)
                    if hasDiscussion {
                        Circle()
                            .fill(Color.accentColor)
                            .frame(width: 8, height: 8)
                            .offset(x: 4, y: -2)
                    }
                }
            }
            .accessibilityLabel("Discuss")

            Spacer()

            Button(role: .destructive, action: onDelete) {
                Image(systemName: "trash")
                    .font(.title3)
            }
            .accessibilityLabel("Delete")
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(.ultraThinMaterial, in: Capsule())
    }

    private func actionButton(
        systemImage: String,
        tint: Color,
        action: @escaping () -> Void
    ) -> some View {
        Button(action: action) {
            Image(systemName: systemImage)
                .font(.title3)
                .foregroundStyle(tint)
        }
    }
}
