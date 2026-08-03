import Foundation

struct NutritionEntry: Codable, Hashable, Sendable {
    var hour: Int
    var food: String

    enum CodingKeys: String, CodingKey {
        case hour
        case food
    }
}

struct DiaryEntry: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let date: String
    var howWasTheDay: String?
    var majorEvents: String?
    var generalContent: String?
    var dayLog: [String: String]?
    var nutritionEntries: [NutritionEntry]?
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
        case nutritionEntries = "nutrition_entries"
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
    var nutritionEntries: [NutritionEntry]?

    enum CodingKeys: String, CodingKey {
        case date
        case userId = "user_id"
        case howWasTheDay = "how_was_the_day"
        case majorEvents = "major_events"
        case generalContent = "general_content"
        case dayLog = "day_log"
        case nutritionEntries = "nutrition_entries"
    }
}

struct NutritionTemplate: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let userId: UUID
    var hour: Int
    var nutrition: String
    var isActive: Bool
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case userId = "user_id"
        case hour
        case nutrition
        case isActive = "is_active"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct NutritionTemplateInsert: Encodable, Sendable {
    let userId: UUID
    let hour: Int
    let nutrition: String
    let isActive: Bool

    enum CodingKeys: String, CodingKey {
        case userId = "user_id"
        case hour
        case nutrition
        case isActive = "is_active"
    }
}

struct NutritionTemplateUpdate: Encodable, Sendable {
    let hour: Int
    let nutrition: String
    let isActive: Bool

    enum CodingKeys: String, CodingKey {
        case hour
        case nutrition
        case isActive = "is_active"
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
