import SwiftUI

struct KbitDiscussionSheet: View {
    let bit: KnowledgeBit
    let apiClient: APIClient

    @Environment(\.dismiss) private var dismiss
    @State private var conversationId: UUID?
    @State private var messages: [ChatMessage] = []
    @State private var draft = ""
    @State private var isLoading = true
    @State private var isStreaming = false
    @State private var errorMessage: String?
    @FocusState private var focused: Bool

    var body: some View {
        NavigationStack {
            VStack(spacing: 0) {
                VStack(alignment: .leading, spacing: 6) {
                    Text(bit.title)
                        .font(.subheadline.weight(.semibold))
                        .lineLimit(2)
                    Text(bit.content)
                        .font(.caption)
                        .foregroundStyle(.secondary)
                        .lineLimit(3)
                }
                .frame(maxWidth: .infinity, alignment: .leading)
                .padding(.horizontal, 16)
                .padding(.vertical, 10)

                Divider()

                ScrollViewReader { proxy in
                    ScrollView {
                        LazyVStack(alignment: .leading, spacing: 12) {
                            if isLoading {
                                ProgressView()
                                    .frame(maxWidth: .infinity)
                                    .padding(.vertical, 32)
                            } else if let errorMessage, messages.isEmpty {
                                Text(errorMessage)
                                    .font(.footnote)
                                    .foregroundStyle(.red)
                                    .padding()
                            } else if messages.isEmpty {
                                ContentUnavailableView(
                                    "Start the discussion",
                                    systemImage: "bubble.left.and.bubble.right",
                                    description: Text("Add a comment to talk about this with Sakhi.")
                                )
                                .padding(.top, 24)
                            } else {
                                ForEach(messages) { message in
                                    MessageBubbleView(
                                        message: message,
                                        isStreaming: isStreaming
                                            && message.id == messages.last?.id
                                            && message.role == .assistant
                                    )
                                    .id(message.id)
                                }
                            }
                        }
                        .padding(16)
                    }
                    .onChange(of: messages) { _, value in
                        if let last = value.last?.id {
                            withAnimation(.easeOut(duration: 0.2)) {
                                proxy.scrollTo(last, anchor: .bottom)
                            }
                        }
                    }
                }

                if let errorMessage, !messages.isEmpty {
                    Text(errorMessage)
                        .font(.caption)
                        .foregroundStyle(.red)
                        .padding(.horizontal, 16)
                }

                HStack(alignment: .bottom, spacing: 10) {
                    TextField("Add a comment…", text: $draft, axis: .vertical)
                        .lineLimit(1...5)
                        .focused($focused)
                        .padding(12)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))

                    Button {
                        Task { await send() }
                    } label: {
                        Image(systemName: "arrow.up.circle.fill")
                            .font(.system(size: 30))
                    }
                    .disabled(isStreaming || draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
                .padding(12)
                .background(.ultraThinMaterial)
            }
            .navigationTitle("Discussion")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button("Done") { dismiss() }
                }
            }
            .task { await bootstrap() }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }

    private func bootstrap() async {
        isLoading = true
        errorMessage = nil
        defer { isLoading = false }
        do {
            let id = try await KbitService.ensureDiscussion(api: apiClient, kbitId: bit.id)
            conversationId = id
            messages = try await ChatService.loadMessages(api: apiClient, conversationId: id)
        } catch {
            errorMessage = error.localizedDescription
        }
    }

    private func send() async {
        let text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !text.isEmpty, !isStreaming else { return }
        guard let conversationId else {
            errorMessage = "Discussion is not ready yet."
            return
        }

        draft = ""
        errorMessage = nil
        messages.append(ChatMessage(role: .user, text: text))
        messages.append(ChatMessage(role: .assistant, text: ""))
        isStreaming = true

        await ChatService.streamMessage(
            api: apiClient,
            conversationId: conversationId,
            text: text,
            model: nil as String?,
            attachmentIds: [],
            onDelta: { delta in
                if let last = messages.indices.last {
                    messages[last].text += delta
                }
            },
            onTool: { step in
                if let last = messages.indices.last, messages[last].role == .assistant {
                    messages[last].toolSteps = ChatMessageToolSteps.apply(
                        step,
                        to: messages[last].toolSteps
                    )
                }
            },
            onDone: { _ in
                isStreaming = false
            },
            onError: { message in
                isStreaming = false
                errorMessage = message
                if let last = messages.indices.last,
                   messages[last].role == .assistant,
                   messages[last].text.isEmpty {
                    messages.removeLast()
                }
            }
        )
    }
}
