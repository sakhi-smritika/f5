import Foundation

struct DiaryEntry: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let date: String
    var howWasTheDay: String?
    var majorEvents: String?
    var generalContent: String?
    var dayLog: [String: String]?
    let createdAt: String?
    let updatedAt: String?
    let userId: UUID

    enum CodingKeys: String, CodingKey {
        case id
        case date
        case howWasTheDay = "how_was_the_day"
        case majorEvents = "major_events"
        case generalContent = "general_content"
        case dayLog = "day_log"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case userId = "user_id"
    }
}

struct DiaryUpsert: Encodable, Sendable {
    let date: String
    let userId: UUID
    var howWasTheDay: String?
    var majorEvents: String?
    var generalContent: String?
    var dayLog: [String: String]?

    enum CodingKeys: String, CodingKey {
        case date
        case userId = "user_id"
        case howWasTheDay = "how_was_the_day"
        case majorEvents = "major_events"
        case generalContent = "general_content"
        case dayLog = "day_log"
    }
}

struct Goal: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    var goalName: String
    var goalDescription: String?
    var progress: String?
    var parentGoal: UUID?
    let userId: UUID
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case goalName = "goal_name"
        case goalDescription = "goal_description"
        case progress
        case parentGoal = "parent_goal"
        case userId = "user_id"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct GoalInsert: Encodable, Sendable {
    let goalName: String
    let goalDescription: String?
    let progress: String?
    let parentGoal: UUID?
    let userId: UUID

    enum CodingKeys: String, CodingKey {
        case goalName = "goal_name"
        case goalDescription = "goal_description"
        case progress
        case parentGoal = "parent_goal"
        case userId = "user_id"
    }
}

struct GoalUpdate: Encodable, Sendable {
    let goalName: String
    let goalDescription: String?
    let progress: String?

    enum CodingKeys: String, CodingKey {
        case goalName = "goal_name"
        case goalDescription = "goal_description"
        case progress
    }
}

struct Profile: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    var username: String?
    var displayName: String?
    var fullName: String?
    var userInformation: String?
    var systemInstructions: String?
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case username
        case displayName = "display_name"
        case fullName = "full_name"
        case userInformation = "user_information"
        case systemInstructions = "system_instructions"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct ProfileUpdate: Encodable, Sendable {
    let fullName: String?
    let userInformation: String?
    let systemInstructions: String?

    enum CodingKeys: String, CodingKey {
        case fullName = "full_name"
        case userInformation = "user_information"
        case systemInstructions = "system_instructions"
    }
}
