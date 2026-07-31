import Foundation

/// Persists kbit pipeline strategy weights and per-graph weights in UserDefaults.
final class StrategyPreferencesStore: Sendable {
    static let shared = StrategyPreferencesStore()

    private let defaults: UserDefaults
    private let stagePrefix = "kbits.strategy."
    private let graphPrefix = "kbits.graphWeight."

    init(defaults: UserDefaults = .standard) {
        self.defaults = defaults
    }

    func weight(for stage: String, strategy: String, default defaultValue: Double = 50) -> Double {
        let key = stagePrefix + stage + "." + strategy
        if defaults.object(forKey: key) == nil {
            return defaultValue
        }
        return defaults.double(forKey: key)
    }

    func setWeight(for stage: String, strategy: String, value: Double) {
        defaults.set(value, forKey: stagePrefix + stage + "." + strategy)
    }

    func graphWeight(for graphId: UUID, default defaultValue: Double = 50) -> Double {
        let key = graphPrefix + graphId.uuidString.lowercased()
        if defaults.object(forKey: key) == nil {
            return defaultValue
        }
        return defaults.double(forKey: key)
    }

    func setGraphWeight(graphId: UUID, value: Double) {
        defaults.set(value, forKey: graphPrefix + graphId.uuidString.lowercased())
    }

    func removeGraphWeight(graphId: UUID) {
        defaults.removeObject(forKey: graphPrefix + graphId.uuidString.lowercased())
    }

    func strategyWeightsPayload(catalog: StrategyCatalog) -> StrategyWeightsPayload {
        StrategyWeightsPayload(
            query: stagePayload(stage: "query", options: catalog.query.options),
            generator: stagePayload(stage: "generator", options: catalog.generator.options),
            screen: stagePayload(stage: "screen", options: catalog.screen.options),
            rank: stagePayload(stage: "rank", options: catalog.rank.options)
        )
    }

    func graphWeightsPayload(graphs: [KnowledgeGraph]) -> [String: Double] {
        Dictionary(
            uniqueKeysWithValues: graphs.map { graph in
                (
                    graph.id.uuidString.lowercased(),
                    graphWeight(for: graph.id)
                )
            }
        )
    }

    private func stagePayload(stage: String, options: [String]) -> [String: Double]? {
        let weights = Dictionary(
            uniqueKeysWithValues: options.map { ($0, weight(for: stage, strategy: $0)) }
        )
        return weights.isEmpty ? nil : weights
    }
}

struct StrategyWeightsPayload: Encodable, Sendable {
    var query: [String: Double]?
    var generator: [String: Double]?
    var screen: [String: Double]?
    var rank: [String: Double]?
}
