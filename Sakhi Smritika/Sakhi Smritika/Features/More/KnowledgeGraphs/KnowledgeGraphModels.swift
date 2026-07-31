import Foundation

struct KnowledgeGraph: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    var title: String
    var description: String?
    let userId: UUID
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case description
        case userId = "user_id"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct KnowledgeGraphInsert: Encodable, Sendable {
    let title: String
    let description: String?
    let userId: UUID

    enum CodingKeys: String, CodingKey {
        case title
        case description
        case userId = "user_id"
    }
}

struct KnowledgeNodeInsert: Encodable, Sendable {
    let graphId: UUID
    let label: String

    enum CodingKeys: String, CodingKey {
        case graphId = "graph_id"
        case label
    }
}

struct KnowledgeNode: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let graphId: UUID
    let label: String
    var description: String?
    var kbitCount: Int
    var userInterest: Double

    enum CodingKeys: String, CodingKey {
        case id
        case graphId = "graph_id"
        case label
        case description
        case kbitCount = "kbit_count"
        case userInterest = "user_interest"
    }
}
