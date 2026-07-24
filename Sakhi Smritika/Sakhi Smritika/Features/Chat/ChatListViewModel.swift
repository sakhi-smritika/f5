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
    var isLoading = true
    var loadError: String?
    var models: [ChatModel] = []
    var selectedModelId: String = ""

    var showNewFolderAlert = false
    var newFolderName = ""
    var folderToDelete: ChatFolder?
    var conversationToDelete: Conversation?

    private let authService: AuthService
    private let apiClient: APIClient

    init(authService: AuthService, apiClient: APIClient) {
        self.authService = authService
        self.apiClient = apiClient
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

    func load() async {
        isLoading = true
        loadError = nil
        defer { isLoading = false }

        do {
            async let foldersTask = ChatService.listFolders()
            async let conversationsTask = ChatService.listConversations()

            folders = try await foldersTask
            conversations = try await conversationsTask
        } catch {
            loadError = error.localizedDescription
            return
        }

        do {
            let modelsResponse = try await ChatService.listModels(api: apiClient)
            models = modelsResponse.models
            if let stored = ChatModelStorage.stored,
               models.contains(where: { $0.id == stored }) {
                selectedModelId = stored
            } else {
                selectedModelId = modelsResponse.defaultModel
            }
        } catch {
            models = []
            selectedModelId = ""
            loadError = "Models unavailable: \(error.localizedDescription)"
        }
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
        } catch {
            loadError = error.localizedDescription
        }
    }

    func deleteFolder(_ folder: ChatFolder) async {
        do {
            try await ChatService.deleteFolder(api: apiClient, id: folder.id)
            folders.removeAll { $0.id == folder.id }
            conversations.removeAll { $0.folderId == folder.id }
            expandedFolderIds.remove(folder.id)
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
        } catch {
            loadError = error.localizedDescription
        }
    }

    func deleteConversation(_ conversation: Conversation) async {
        do {
            try await ChatService.deleteConversation(api: apiClient, id: conversation.id)
            conversations.removeAll { $0.id == conversation.id }
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
    }
}
