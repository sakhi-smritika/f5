import SwiftUI

private enum KbitCardPage: Hashable {
    case content
    case prompt
    case metadata
}

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

    @State private var cardPage = 0

    private var hasPromptCard: Bool {
        guard let prompt = bit.generatorPrompt else { return false }
        return !prompt.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
    }

    private var hasMetadataCard: Bool {
        bit.metadata != nil
    }

    private var pages: [KbitCardPage] {
        var result: [KbitCardPage] = [.content]
        if hasPromptCard { result.append(.prompt) }
        if hasMetadataCard { result.append(.metadata) }
        return result
    }

    private var showsPageIndicator: Bool {
        pages.count > 1
    }

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
            TabView(selection: $cardPage) {
                ForEach(Array(pages.enumerated()), id: \.offset) { index, page in
                    pageView(page, in: size)
                        .tag(index)
                }
            }
            .tabViewStyle(.page(indexDisplayMode: showsPageIndicator ? .automatic : .never))
            .id(bit.id)

            actionBar
                .padding(.horizontal, 16)
                .padding(.bottom, showsPageIndicator ? 28 : 16)
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

    @ViewBuilder
    private func pageView(_ page: KbitCardPage, in size: CGSize) -> some View {
        switch page {
        case .content:
            knowledgeBitPage(in: size)
        case .prompt:
            if let prompt = bit.generatorPrompt {
                promptPage(prompt, in: size)
            }
        case .metadata:
            if let metadata = bit.metadata {
                metadataPage(metadata, in: size)
            }
        }
    }

    private func knowledgeBitPage(in size: CGSize) -> some View {
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
    }

    private func promptPage(_ prompt: String, in size: CGSize) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 16) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Generation prompt")
                        .font(.title2.weight(.semibold))

                    Text("The instruction sent to the AI when this bit was created.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                Text(prompt)
                    .font(.body.monospaced())
                    .foregroundStyle(.primary)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .textSelection(.enabled)

                Spacer(minLength: 88)
            }
            .padding(20)
            .frame(minHeight: size.height - 20)
        }
        .scrollIndicators(.hidden)
    }

    private func metadataPage(_ metadata: KbitMetadata, in size: CGSize) -> some View {
        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                VStack(alignment: .leading, spacing: 6) {
                    Text("Generation metadata")
                        .font(.title2.weight(.semibold))
                    Text("How this bit was produced.")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }

                metadataSection(title: "Strategies") {
                    if let value = metadata.queryStrategy {
                        metadataRow("Query", value)
                    }
                    if let value = metadata.generatorStrategy {
                        metadataRow("Generator", value)
                    }
                    if let value = metadata.screenStrategy {
                        metadataRow("Screen", value)
                    }
                    if let value = metadata.rankStrategy {
                        metadataRow("Rank", value)
                    }
                }

                if let graph = metadata.graph {
                    metadataSection(title: "Knowledge graph") {
                        metadataRow("Graph", graph.title ?? graph.id)
                    }
                }

                if let node = metadata.expansionNode {
                    metadataSection(title: "Expansion node") {
                        metadataRow("Concept", node.label)
                    }
                }

                if let concepts = metadata.newConcepts, !concepts.isEmpty {
                    metadataSection(title: "New concepts") {
                        ForEach(concepts, id: \.self) { concept in
                            Text(concept)
                                .font(.body)
                                .frame(maxWidth: .infinity, alignment: .leading)
                        }
                    }
                }

                Spacer(minLength: 88)
            }
            .padding(20)
            .frame(minHeight: size.height - 20)
        }
        .scrollIndicators(.hidden)
    }

    private func metadataSection(title: String, @ViewBuilder content: () -> some View) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.headline)
            content()
        }
    }

    private func metadataRow(_ label: String, _ value: String) -> some View {
        HStack(alignment: .top) {
            Text(label)
                .font(.subheadline.weight(.medium))
                .foregroundStyle(.secondary)
                .frame(width: 88, alignment: .leading)
            Text(value)
                .font(.body.monospaced())
                .frame(maxWidth: .infinity, alignment: .leading)
        }
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
