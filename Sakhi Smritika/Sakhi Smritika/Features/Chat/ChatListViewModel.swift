import Auth
import Foundation
import Observation

private enum ChatModelStorage {
    static let key = "f5-chat-model"

    static var stored: String? {
        get { UserDefaults.standard.string(forKey: key) }
        set { UserDefaults.standard.set(newValue, forKey: key) }
    }
}

@MainActor
@Observable
final class ChatListViewModel {
    var folders: [ChatFolder] = []
    var conversations: [Conversation] = []
    var expandedFolderIds: Set<UUID> = []
    var loadError: String?
    var models: [ChatModel] = []
    var selectedModelId: String = ""

    var showNewFolderAlert = false
    var newFolderName = ""
    var folderToDelete: ChatFolder?
    var conversationToDelete: Conversation?

    private(set) var isRefreshing = false
    private(set) var hasData = false

    /// Only block the list with a spinner when there is nothing cached to show.
    var isLoading: Bool { isRefreshing && !hasData }

    private let authService: AuthService
    private let apiClient: APIClient
    private let cache: CacheStore
    private let refreshTracker: SessionRefreshTracker
    private let threadRegistry: ChatThreadRegistry

    init(
        authService: AuthService,
        apiClient: APIClient,
        cache: CacheStore,
        refreshTracker: SessionRefreshTracker,
        threadRegistry: ChatThreadRegistry
    ) {
        self.authService = authService
        self.apiClient = apiClient
        self.cache = cache
        self.refreshTracker = refreshTracker
        self.threadRegistry = threadRegistry
        readFromCache()
    }

    var unfolderedConversations: [Conversation] {
        conversations
            .filter { $0.folderId == nil }
            .sorted { ($0.updatedAt ?? "") > ($1.updatedAt ?? "") }
    }

    func conversations(in folderId: UUID) -> [Conversation] {
        conversations
            .filter { $0.folderId == folderId }
            .sorted { ($0.updatedAt ?? "") > ($1.updatedAt ?? "") }
    }

    /// Runs on every appearance of the Chat tab. Re-reading the local store is
    /// free and picks up conversations created elsewhere in the app (a knowledge
    /// bit discussion, for instance); the network is only touched once per launch.
    func appear() async {
        readFromCache()
        if refreshTracker.claim(RefreshKey.conversations) {
            await refreshList()
        }
        if refreshTracker.claim(RefreshKey.chatModels) {
            await refreshModels()
        }
    }

    /// Pull to refresh always goes to the network.
    func reload() async {
        _ = refreshTracker.claim(RefreshKey.conversations)
        _ = refreshTracker.claim(RefreshKey.chatModels)
        await refreshList()
        await refreshModels()
    }

    /// Hands back the live view model for a thread, so a draft, an upload in
    /// progress, or a running stream survives navigating away and back.
    func threadViewModel(for route: ChatThreadRegistry.Key) -> ChatThreadViewModel {
        let viewModel = threadRegistry.viewModel(for: route) { [self] in
            let conversation: Conversation?
            switch route {
            case .conversation(let id):
                conversation = conversations.first(where: { $0.id == id })
            case .draft, .kbit:
                conversation = nil
            }
            return ChatThreadViewModel(
                conversation: conversation,
                models: models,
                selectedModelId: selectedModelId,
                apiClient: apiClient,
                cache: cache,
                refreshTracker: refreshTracker
            )
        }
        // Rebound every time because a thread first opened from the Kbits tab can
        // later be presented by this list.
        viewModel.onConversationUpdated = { [weak self] updated in
            self?.upsertConversation(updated)
        }
        return viewModel
    }

    private func readFromCache() {
        folders = cache.folders()
        conversations = cache.conversations()
        hasData = cache.hasSynced(RefreshKey.conversations)

        if let cached = cache.chatModels() {
            models = cached.models
            selectedModelId = resolvedModelId(for: cached)
        }
    }

    private func refreshList() async {
        isRefreshing = true
        loadError = nil
        defer { isRefreshing = false }

        do {
            async let foldersTask = ChatService.listFolders()
            async let conversationsTask = ChatService.listConversations()

            let loadedFolders = try await foldersTask
            let loadedConversations = try await conversationsTask

            folders = loadedFolders
            conversations = loadedConversations
            hasData = true

            cache.replaceFolders(loadedFolders)
            cache.replaceConversations(loadedConversations)
            cache.markSynced(RefreshKey.conversations)
        } catch {
            loadError = error.localizedDescription
            refreshTracker.release(RefreshKey.conversations)
        }
    }

    private func refreshModels() async {
        do {
            let response = try await ChatService.listModels(api: apiClient)
            models = response.models
            selectedModelId = resolvedModelId(for: response)
            cache.setChatModels(response)
        } catch {
            refreshTracker.release(RefreshKey.chatModels)
            // Keep whatever the cache already gave us; only surface the failure
            // when there is nothing to pick from.
            if models.isEmpty {
                selectedModelId = ""
                loadError = "Models unavailable: \(error.localizedDescription)"
            }
        }
    }

    private func resolvedModelId(for response: ChatModelsResponse) -> String {
        if let stored = ChatModelStorage.stored,
           response.models.contains(where: { $0.id == stored }) {
            return stored
        }
        return response.defaultModel
    }

    func selectModel(_ id: String) {
        selectedModelId = id
        ChatModelStorage.stored = id
    }

    func toggleFolder(_ id: UUID) {
        if expandedFolderIds.contains(id) {
            expandedFolderIds.remove(id)
        } else {
            expandedFolderIds.insert(id)
        }
    }

    func createFolder() async {
        guard let userId = authService.user?.id else { return }
        let name = newFolderName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else { return }
        do {
            let folder = try await ChatService.createFolder(name: name, userId: userId)
            folders.append(folder)
            folders.sort { $0.name.localizedCaseInsensitiveCompare($1.name) == .orderedAscending }
            cache.upsertFolder(folder)
            newFolderName = ""
            showNewFolderAlert = false
            expandedFolderIds.insert(folder.id)
        } catch {
            loadError = error.localizedDescription
        }
    }

    func renameFolder(_ folder: ChatFolder, to name: String) async {
        let trimmed = name.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        do {
            let updated = try await ChatService.renameFolder(id: folder.id, name: trimmed)
            if let index = folders.firstIndex(where: { $0.id == folder.id }) {
                folders[index] = updated
            }
            cache.upsertFolder(updated)
        } catch {
            loadError = error.localizedDescription
        }
    }

    func deleteFolder(_ folder: ChatFolder) async {
        do {
            try await ChatService.deleteFolder(api: apiClient, id: folder.id)
            let removedIds = conversations.filter { $0.folderId == folder.id }.map(\.id)
            folders.removeAll { $0.id == folder.id }
            conversations.removeAll { $0.folderId == folder.id }
            expandedFolderIds.remove(folder.id)

            cache.deleteConversations(folderId: folder.id)
            cache.deleteFolder(id: folder.id)
            for id in removedIds {
                cache.deleteKbitDiscussion(conversationId: id)
                threadRegistry.remove(conversationId: id)
            }
        } catch {
            loadError = error.localizedDescription
        }
    }

    func renameConversation(_ conversation: Conversation, to title: String) async {
        let trimmed = title.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !trimmed.isEmpty else { return }
        do {
            try await ChatService.renameConversation(api: apiClient, id: conversation.id, title: trimmed)
            if let index = conversations.firstIndex(where: { $0.id == conversation.id }) {
                conversations[index].title = trimmed
            }
            cache.setConversationTitle(id: conversation.id, title: trimmed)
        } catch {
            loadError = error.localizedDescription
        }
    }

    func moveConversation(_ conversation: Conversation, to folderId: UUID?) async {
        do {
            try await ChatService.moveConversation(api: apiClient, id: conversation.id, folderId: folderId)
            if let index = conversations.firstIndex(where: { $0.id == conversation.id }) {
                conversations[index].folderId = folderId
            }
            cache.setConversationFolder(id: conversation.id, folderId: folderId)
        } catch {
            loadError = error.localizedDescription
        }
    }

    func deleteConversation(_ conversation: Conversation) async {
        do {
            try await ChatService.deleteConversation(api: apiClient, id: conversation.id)
            conversations.removeAll { $0.id == conversation.id }
            cache.deleteConversation(id: conversation.id)
            cache.deleteKbitDiscussion(conversationId: conversation.id)
            threadRegistry.remove(conversationId: conversation.id)
        } catch {
            loadError = error.localizedDescription
        }
    }

    func upsertConversation(_ conversation: Conversation) {
        if let index = conversations.firstIndex(where: { $0.id == conversation.id }) {
            var merged = conversations[index]
            if let title = conversation.title {
                merged.title = title
            }
            if let updatedAt = conversation.updatedAt {
                merged.updatedAt = updatedAt
            }
            if conversation.folderId != nil {
                merged.folderId = conversation.folderId
            }
            if conversation.kbitId != nil {
                merged.kbitId = conversation.kbitId
            }
            conversations[index] = merged
        } else {
            conversations.insert(conversation, at: 0)
        }
        conversations.sort { ($0.updatedAt ?? "") > ($1.updatedAt ?? "") }
        cache.mergeConversation(conversation)
    }
}
