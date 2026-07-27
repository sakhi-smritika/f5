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
    var isStreaming = false
    var loadError: String?
    var sendError: String?
    var quote: String?

    var models: [ChatModel]
    var selectedModelId: String

    private(set) var isRefreshing = false
    private(set) var hasMessages = false

    /// Only block the thread with a spinner when there is nothing cached to show.
    var isLoading: Bool { isRefreshing && !hasMessages }

    /// Rebound by whichever screen is presenting this thread, so the chat list
    /// can update live. Not observed — it is set during view construction.
    @ObservationIgnored
    var onConversationUpdated: (@MainActor (Conversation) -> Void)?

    private let apiClient: APIClient
    private let cache: CacheStore
    private let refreshTracker: SessionRefreshTracker
    /// Set for a knowledge bit discussion, whose conversation is resolved by the
    /// backend rather than passed in.
    private let bootstrapKbit: KnowledgeBit?

    init(
        conversation: Conversation?,
        models: [ChatModel],
        selectedModelId: String,
        apiClient: APIClient,
        cache: CacheStore,
        refreshTracker: SessionRefreshTracker,
        bootstrapKbit: KnowledgeBit? = nil
    ) {
        self.apiClient = apiClient
        self.cache = cache
        self.refreshTracker = refreshTracker
        self.bootstrapKbit = bootstrapKbit
        self.models = models
        self.selectedModelId = selectedModelId

        self.conversationId = conversation?.id
            ?? bootstrapKbit.flatMap { cache.kbitDiscussionConversationId(kbitId: $0.id) }
        self.kbitId = conversation?.kbitId ?? bootstrapKbit?.id
        self.title = bootstrapKbit?.title ?? conversation?.displayTitle ?? "New chat"

        if let bootstrapKbit {
            pinnedKbit = bootstrapKbit
        } else if let kbitId, let cached = cache.kbit(id: kbitId) {
            pinnedKbit = cached
            if title == "New chat" || title.isEmpty {
                title = cached.title
            }
        }

        if let conversationId, let cached = cache.messages(conversationId: conversationId) {
            messages = cached
            hasMessages = true
        }
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

    /// Picks up the model list once the chat list has it, for threads that were
    /// created before it finished loading.
    func syncModels(_ models: [ChatModel], selectedModelId: String) {
        guard !models.isEmpty else { return }
        self.models = models
        if !models.contains(where: { $0.id == self.selectedModelId }) {
            self.selectedModelId = selectedModelId
        }
    }

    /// Runs on every appearance. Cached messages are already on screen from
    /// `init`; the network is only touched once per launch per conversation.
    func appear() async {
        await resolveDiscussionIfNeeded()
        guard let conversationId else { return }

        if !hasMessages, let cached = cache.messages(conversationId: conversationId) {
            messages = cached
            hasMessages = true
        }

        async let pinnedTask: () = refreshPinnedKbitIfNeeded()
        if refreshTracker.claim(RefreshKey.messages(conversationId)) {
            await refreshMessages(conversationId: conversationId)
        }
        await pinnedTask
    }

    /// Pull to refresh always goes to the network.
    func reload() async {
        await resolveDiscussionIfNeeded()
        guard let conversationId else { return }
        _ = refreshTracker.claim(RefreshKey.messages(conversationId))
        await refreshMessages(conversationId: conversationId)
    }

    private func refreshMessages(conversationId: UUID) async {
        guard !isStreaming else { return }
        isRefreshing = true
        loadError = nil
        defer { isRefreshing = false }

        do {
            let loaded = try await ChatService.loadMessages(
                api: apiClient,
                conversationId: conversationId
            )
            // A send that started while this was in flight owns the transcript.
            guard !isStreaming else { return }
            messages = loaded
            hasMessages = true
            cache.replaceMessages(loaded, conversationId: conversationId)
        } catch {
            refreshTracker.release(RefreshKey.messages(conversationId))
            if !hasMessages {
                loadError = error.localizedDescription
            }
        }
    }

    /// Resolves a knowledge bit discussion's conversation the first time it is
    /// opened. Later launches read the mapping straight from the cache.
    private func resolveDiscussionIfNeeded() async {
        guard conversationId == nil, let bootstrapKbit else { return }
        do {
            let id = try await KbitService.ensureDiscussion(api: apiClient, kbitId: bootstrapKbit.id)
            conversationId = id
            cache.setKbitDiscussion(kbitId: bootstrapKbit.id, conversationId: id)
            if let cached = cache.messages(conversationId: id) {
                messages = cached
                hasMessages = true
            }
        } catch {
            loadError = error.localizedDescription
        }
    }

    private func refreshPinnedKbitIfNeeded() async {
        guard let kbitId else {
            pinnedKbit = nil
            return
        }
        if pinnedKbit == nil, let cached = cache.kbit(id: kbitId) {
            pinnedKbit = cached
            applyKbitTitleIfUnnamed(cached)
        }
        guard refreshTracker.claim(RefreshKey.pinnedKbit(kbitId)) else { return }
        do {
            guard let bit = try await KbitService.getKbit(id: kbitId) else { return }
            pinnedKbit = bit
            cache.setKbit(bit)
            applyKbitTitleIfUnnamed(bit)
        } catch {
            refreshTracker.release(RefreshKey.pinnedKbit(kbitId))
        }
    }

    private func applyKbitTitleIfUnnamed(_ bit: KnowledgeBit) {
        if title == "New chat" || title.isEmpty {
            title = bit.title
        }
    }

    func ensureConversation() async throws -> UUID {
        if let conversationId { return conversationId }

        if let bootstrapKbit {
            let id = try await KbitService.ensureDiscussion(api: apiClient, kbitId: bootstrapKbit.id)
            conversationId = id
            cache.setKbitDiscussion(kbitId: bootstrapKbit.id, conversationId: id)
            return id
        }

        let created = try await ChatService.createConversation(api: apiClient)
        conversationId = created.id
        title = created.title?.nilIfEmpty ?? "New chat"
        let now = ISO8601DateFormatter().string(from: Date())
        let conversation = Conversation(
            id: created.id,
            title: created.title,
            folderId: created.folderId,
            createdAt: now,
            updatedAt: now,
            kbitId: nil
        )
        cache.upsertConversation(conversation)
        onConversationUpdated?(conversation)
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
        hasMessages = true

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
                    self.cache.replaceMessages(self.messages, conversationId: id)
                    self.cache.mergeConversation(updated)
                    // The local transcript is now complete, so reopening this
                    // thread should not refetch it during this launch.
                    _ = self.refreshTracker.claim(RefreshKey.messages(id))
                    self.onConversationUpdated?(updated)
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
                    self.cache.replaceMessages(self.messages, conversationId: id)
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
