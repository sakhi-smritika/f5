import Foundation
import Observation

@MainActor
@Observable
final class StrategiesViewModel {
    var catalog: StrategyCatalog?
    var graphs: [KnowledgeGraph] = []
    var isLoading = false
    var loadError: String?

    private let apiClient: APIClient
    let preferences = StrategyPreferencesStore.shared

    init(apiClient: APIClient) {
        self.apiClient = apiClient
    }

    func appear() async {
        isLoading = true
        loadError = nil
        defer { isLoading = false }
        do {
            async let catalogTask = KbitService.strategies(api: apiClient)
            async let graphsTask = KnowledgeGraphService.listGraphs()
            catalog = try await catalogTask
            graphs = try await graphsTask
        } catch {
            loadError = error.localizedDescription
        }
    }

    func weight(for stage: String, strategy: String) -> Double {
        preferences.weight(for: stage, strategy: strategy)
    }

    func setWeight(for stage: String, strategy: String, value: Double) {
        preferences.setWeight(for: stage, strategy: strategy, value: value)
    }

    func graphWeight(for graphId: UUID) -> Double {
        preferences.graphWeight(for: graphId)
    }

    func setGraphWeight(for graphId: UUID, value: Double) {
        preferences.setGraphWeight(graphId: graphId, value: value)
    }
}
