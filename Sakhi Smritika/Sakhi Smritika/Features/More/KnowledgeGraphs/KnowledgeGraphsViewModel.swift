import Auth
import Foundation
import Observation

@MainActor
@Observable
final class KnowledgeGraphsViewModel {
    var graphs: [KnowledgeGraph] = []
    var isLoading = false
    var loadError: String?

    var showCreate = false
    var newTitle = ""
    var newDescription = ""
    var newFirstNode = ""
    var createStatus: SaveStatus = .idle

    enum SaveStatus: Equatable {
        case idle
        case saving
        case error(String)
    }

    private let authService: AuthService

    init(authService: AuthService) {
        self.authService = authService
    }

    func appear() async {
        await reload()
    }

    func reload() async {
        isLoading = true
        loadError = nil
        defer { isLoading = false }
        do {
            graphs = try await KnowledgeGraphService.listGraphs()
        } catch {
            loadError = error.localizedDescription
        }
    }

    func create() async {
        guard let userId = authService.user?.id else { return }
        let title = newTitle.trimmingCharacters(in: .whitespacesAndNewlines)
        let firstNode = newFirstNode.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !title.isEmpty, !firstNode.isEmpty else {
            createStatus = .error("Title and first node are required.")
            return
        }

        createStatus = .saving
        do {
            let graph = try await KnowledgeGraphService.create(
                title: title,
                description: newDescription.nilIfEmpty,
                firstNodeLabel: firstNode,
                userId: userId
            )
            graphs.insert(graph, at: 0)
            newTitle = ""
            newDescription = ""
            newFirstNode = ""
            showCreate = false
            createStatus = .idle
        } catch {
            createStatus = .error(error.localizedDescription)
        }
    }

    func delete(_ graph: KnowledgeGraph) async {
        do {
            try await KnowledgeGraphService.delete(id: graph.id)
            graphs.removeAll { $0.id == graph.id }
            StrategyPreferencesStore.shared.removeGraphWeight(graphId: graph.id)
        } catch {
            loadError = error.localizedDescription
        }
    }
}

private extension String {
    var nilIfEmpty: String? {
        trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? nil
            : trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
