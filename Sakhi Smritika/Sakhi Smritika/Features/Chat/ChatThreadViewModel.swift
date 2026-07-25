import Foundation
import Observation
import UniformTypeIdentifiers

@MainActor
@Observable
final class ChatThreadViewModel {
    /// `nil` means a local draft that creates a conversation on first send/attach.
    var conversationId: UUID?
    var kbitId: UUID?
    var pinnedKbit: KnowledgeBit?
    var title: String
    var messages: [ChatMessage] = []
    var draft = ""
    var pendingAttachments: [PendingAttachment] = []
    var isLoading = false
    var isStreaming = false
    var loadError: String?
    var sendError: String?
    var quote: String?

    var models: [ChatModel]
    var selectedModelId: String

    private let apiClient: APIClient
    private let onConversationUpdated: (Conversation) -> Void

    init(
        conversation: Conversation?,
        models: [ChatModel],
        selectedModelId: String,
        apiClient: APIClient,
        onConversationUpdated: @escaping (Conversation) -> Void
    ) {
        self.conversationId = conversation?.id
        self.kbitId = conversation?.kbitId
        self.title = conversation?.displayTitle ?? "New chat"
        self.models = models
        self.selectedModelId = selectedModelId
        self.apiClient = apiClient
        self.onConversationUpdated = onConversationUpdated
    }

    var canSend: Bool {
        !isStreaming
            && (!draft.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
                || !pendingAttachments.isEmpty)
            && !pendingAttachments.contains(where: { $0.isUploading })
    }

    var isKbitDiscussion: Bool {
        kbitId != nil
    }

    var selectedModelLabel: String {
        models.first(where: { $0.id == selectedModelId })?.label
            ?? models.first?.label
            ?? "Model"
    }

    func loadIfNeeded() async {
        guard let conversationId else { return }
        isLoading = true
        loadError = nil
        defer { isLoading = false }

        async let pinnedTask: () = loadPinnedKbitIfNeeded()
        do {
            messages = try await ChatService.loadMessages(api: apiClient, conversationId: conversationId)
        } catch {
            loadError = error.localizedDescription
        }
        await pinnedTask
    }

    private func loadPinnedKbitIfNeeded() async {
        guard let kbitId else {
            pinnedKbit = nil
            return
        }
        do {
            pinnedKbit = try await KbitService.getKbit(id: kbitId)
            if let pinnedKbit, title == "New chat" || title.isEmpty {
                title = pinnedKbit.title
            }
        } catch {
            pinnedKbit = nil
        }
    }

    func ensureConversation() async throws -> UUID {
        if let conversationId { return conversationId }
        let created = try await ChatService.createConversation(api: apiClient)
        conversationId = created.id
        title = created.title?.nilIfEmpty ?? "New chat"
        let conversation = Conversation(
            id: created.id,
            title: created.title,
            folderId: created.folderId,
            createdAt: ISO8601DateFormatter().string(from: Date()),
            updatedAt: ISO8601DateFormatter().string(from: Date()),
            kbitId: nil
        )
        onConversationUpdated(conversation)
        return created.id
    }

    func send() async {
        guard canSend else { return }
        var text = draft.trimmingCharacters(in: .whitespacesAndNewlines)
        if let quote, !quote.isEmpty {
            let quoted = quote
                .split(separator: "\n", omittingEmptySubsequences: false)
                .map { "> \($0)" }
                .joined(separator: "\n")
            text = text.isEmpty ? quoted : "\(quoted)\n\n\(text)"
        }
        guard !text.isEmpty || !pendingAttachments.isEmpty else { return }

        sendError = nil
        draft = ""
        quote = nil

        let attachmentSnapshot = pendingAttachments
        let attachmentIds = attachmentSnapshot.map(\.id)
        let chatAttachments = attachmentSnapshot.map {
            ChatAttachment(
                id: $0.id,
                filename: $0.filename,
                mimeType: $0.mimeType,
                sizeBytes: $0.sizeBytes,
                url: nil
            )
        }
        pendingAttachments = []

        // Show the user bubble immediately; stream the assistant reply after.
        messages.append(
            ChatMessage(role: .user, text: text, attachments: chatAttachments.isEmpty ? nil : chatAttachments)
        )
        messages.append(ChatMessage(role: .assistant, text: ""))
        isStreaming = true

        do {
            let id = try await ensureConversation()

            await ChatService.streamMessage(
                api: apiClient,
                conversationId: id,
                text: text.isEmpty ? " " : text,
                model: selectedModelId.isEmpty ? nil : selectedModelId,
                attachmentIds: attachmentIds,
                onDelta: { [weak self] delta in
                    guard let self, let last = self.messages.indices.last else { return }
                    self.messages[last].text += delta
                },
                onTool: { [weak self] step in
                    guard let self, let last = self.messages.indices.last else { return }
                    guard self.messages[last].role == .assistant else { return }
                    self.messages[last].toolSteps = ChatMessageToolSteps.apply(
                        step,
                        to: self.messages[last].toolSteps
                    )
                },
                onDone: { [weak self] newTitle in
                    guard let self else { return }
                    self.isStreaming = false
                    if let newTitle, !newTitle.isEmpty {
                        self.title = newTitle
                    }
                    let updated = Conversation(
                        id: id,
                        title: self.title,
                        folderId: nil,
                        createdAt: nil,
                        updatedAt: ISO8601DateFormatter().string(from: Date()),
                        kbitId: self.kbitId
                    )
                    self.onConversationUpdated(updated)
                },
                onError: { [weak self] message in
                    guard let self else { return }
                    self.isStreaming = false
                    self.sendError = message
                    if let last = self.messages.indices.last,
                       self.messages[last].role == .assistant,
                       self.messages[last].text.isEmpty {
                        self.messages.removeLast()
                    }
                }
            )
        } catch {
            isStreaming = false
            sendError = error.localizedDescription
            if let last = messages.indices.last,
               messages[last].role == .assistant,
               messages[last].text.isEmpty {
                messages.removeLast()
            }
        }
    }

    func addFiles(_ items: [(Data, String, String)]) async {
        do {
            let id = try await ensureConversation()
            for (data, filename, mime) in items {
                let tempId = UUID()
                pendingAttachments.append(
                    PendingAttachment(
                        id: tempId,
                        filename: filename,
                        mimeType: mime,
                        sizeBytes: data.count,
                        isUploading: true
                    )
                )
                do {
                    let uploaded = try await ChatService.uploadAttachment(
                        api: apiClient,
                        conversationId: id,
                        data: data,
                        filename: filename,
                        mimeType: mime
                    )
                    if let index = pendingAttachments.firstIndex(where: { $0.id == tempId }) {
                        pendingAttachments[index] = PendingAttachment(
                            id: uploaded.id,
                            filename: uploaded.filename,
                            mimeType: uploaded.mimeType,
                            sizeBytes: uploaded.sizeBytes,
                            isUploading: false
                        )
                    }
                } catch {
                    if let index = pendingAttachments.firstIndex(where: { $0.id == tempId }) {
                        pendingAttachments[index].isUploading = false
                        pendingAttachments[index].error = error.localizedDescription
                    }
                }
            }
        } catch {
            sendError = error.localizedDescription
        }
    }

    func removePendingAttachment(_ attachment: PendingAttachment) async {
        pendingAttachments.removeAll { $0.id == attachment.id }
        guard let conversationId, attachment.error == nil, !attachment.isUploading else { return }
        try? await ChatService.deleteAttachment(
            api: apiClient,
            conversationId: conversationId,
            attachmentId: attachment.id
        )
    }
}

private extension String {
    var nilIfEmpty: String? {
        trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : self
    }
}
