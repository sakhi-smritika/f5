import Foundation

struct KbitMetadataRef: Codable, Hashable, Sendable {
    let id: String
    let title: String?

    enum CodingKeys: String, CodingKey {
        case id
        case title
    }
}

struct KbitMetadataNode: Codable, Hashable, Sendable {
    let id: String
    let label: String
}

struct KbitMetadata: Codable, Hashable, Sendable {
    let queryStrategy: String?
    let generatorStrategy: String?
    let screenStrategy: String?
    let rankStrategy: String?
    let graph: KbitMetadataRef?
    let expansionNode: KbitMetadataNode?
    let newConcepts: [String]?

    enum CodingKeys: String, CodingKey {
        case queryStrategy = "query_strategy"
        case generatorStrategy = "generator_strategy"
        case screenStrategy = "screen_strategy"
        case rankStrategy = "rank_strategy"
        case graph
        case expansionNode = "expansion_node"
        case newConcepts = "new_concepts"
    }
}

struct KnowledgeBit: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let createdAt: String?
    let updatedAt: String?
    var title: String
    var content: String
    var relatedGoal: UUID?
    var generatorPrompt: String?
    var metadata: KbitMetadata?
    var position: Int
    var isRead: Bool
    var isViewed: Bool
    var isLiked: Bool
    var isDisliked: Bool
    var rating: Double?
    /// Schema typo preserved from backend/DB.
    var isMarkedRelavant: Bool
    /// Schema typo preserved from backend/DB.
    var isMarkedIrrelavant: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case title
        case content
        case relatedGoal = "related_goal"
        case generatorPrompt = "generator_prompt"
        case metadata
        case position
        case isRead = "is_read"
        case isViewed = "is_viewed"
        case isLiked = "is_liked"
        case isDisliked = "is_disliked"
        case rating
        case isMarkedRelavant = "is_marked_relavant"
        case isMarkedIrrelavant = "is_marked_irrelavant"
    }
}

struct StageStrategies: Codable, Sendable {
    let defaultStrategy: String?
    let options: [String]

    enum CodingKeys: String, CodingKey {
        case defaultStrategy = "default"
        case options
    }
}

struct StrategyCatalog: Codable, Sendable {
    let query: StageStrategies
    let generator: StageStrategies
    let screen: StageStrategies
    let rank: StageStrategies
}

struct InvokeKbitsBody: Encodable, Sendable {
    var goalId: UUID? = nil
    var count: Int? = nil
    var strategyWeights: StrategyWeightsPayload? = nil
    var graphWeights: [String: Double]? = nil
    var queryStrategy: String? = nil
    var generatorStrategy: String? = nil
    var screenStrategy: String? = nil
    var rankStrategy: String? = nil

    enum CodingKeys: String, CodingKey {
        case goalId = "goal_id"
        case count
        case strategyWeights = "strategy_weights"
        case graphWeights = "graph_weights"
        case queryStrategy = "query_strategy"
        case generatorStrategy = "generator_strategy"
        case screenStrategy = "screen_strategy"
        case rankStrategy = "rank_strategy"
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        if let goalId { try container.encode(goalId, forKey: .goalId) }
        if let count { try container.encode(count, forKey: .count) }
        if let strategyWeights { try container.encode(strategyWeights, forKey: .strategyWeights) }
        if let graphWeights, !graphWeights.isEmpty {
            try container.encode(graphWeights, forKey: .graphWeights)
        }
        if let queryStrategy, !queryStrategy.isEmpty {
            try container.encode(queryStrategy, forKey: .queryStrategy)
        }
        if let generatorStrategy, !generatorStrategy.isEmpty {
            try container.encode(generatorStrategy, forKey: .generatorStrategy)
        }
        if let screenStrategy, !screenStrategy.isEmpty {
            try container.encode(screenStrategy, forKey: .screenStrategy)
        }
        if let rankStrategy, !rankStrategy.isEmpty {
            try container.encode(rankStrategy, forKey: .rankStrategy)
        }
    }
}

struct InvokeKbitsResponse: Codable, Sendable {
    let count: Int?
    let bits: [KnowledgeBit]
}

struct KbitUpdate: Encodable, Sendable {
    var isRead: Bool? = nil
    var isViewed: Bool? = nil
    var isLiked: Bool? = nil
    var isDisliked: Bool? = nil
    var rating: Double? = nil
    var isMarkedRelavant: Bool? = nil
    var isMarkedIrrelavant: Bool? = nil

    enum CodingKeys: String, CodingKey {
        case isRead = "is_read"
        case isViewed = "is_viewed"
        case isLiked = "is_liked"
        case isDisliked = "is_disliked"
        case rating
        case isMarkedRelavant = "is_marked_relavant"
        case isMarkedIrrelavant = "is_marked_irrelavant"
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        if let isRead { try container.encode(isRead, forKey: .isRead) }
        if let isViewed { try container.encode(isViewed, forKey: .isViewed) }
        if let isLiked { try container.encode(isLiked, forKey: .isLiked) }
        if let isDisliked { try container.encode(isDisliked, forKey: .isDisliked) }
        if let rating { try container.encode(rating, forKey: .rating) }
        if let isMarkedRelavant { try container.encode(isMarkedRelavant, forKey: .isMarkedRelavant) }
        if let isMarkedIrrelavant { try container.encode(isMarkedIrrelavant, forKey: .isMarkedIrrelavant) }
    }
}

struct EnsureDiscussionResponse: Codable, Sendable {
    let conversationId: UUID
    let created: Bool?

    enum CodingKeys: String, CodingKey {
        case conversationId = "conversation_id"
        case created
    }
}
