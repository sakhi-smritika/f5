import Foundation

enum ChatRole: String, Codable, Sendable {
    case user
    case assistant
}

struct ChatAttachment: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    let filename: String
    let mimeType: String
    let sizeBytes: Int
    var url: String?

    enum CodingKeys: String, CodingKey {
        case id
        case filename
        case mimeType = "mime_type"
        case sizeBytes = "size_bytes"
        case url
    }
}

struct ChatMessage: Codable, Identifiable, Hashable, Sendable {
    var id: UUID = UUID()
    var role: ChatRole
    var text: String
    var eventId: String?
    var attachments: [ChatAttachment]?

    enum CodingKeys: String, CodingKey {
        case role
        case text
        case eventId = "event_id"
        case attachments
    }
}

struct ChatFolder: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    var name: String
    let createdAt: String?
    let updatedAt: String?

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case createdAt = "created_at"
        case updatedAt = "updated_at"
    }
}

struct Conversation: Codable, Identifiable, Hashable, Sendable {
    let id: UUID
    var title: String?
    var folderId: UUID?
    let createdAt: String?
    var updatedAt: String?
    var kbitId: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case folderId = "folder_id"
        case createdAt = "created_at"
        case updatedAt = "updated_at"
        case kbitId = "kbit_id"
    }

    var displayTitle: String {
        let trimmed = title?.trimmingCharacters(in: .whitespacesAndNewlines) ?? ""
        return trimmed.isEmpty ? "New chat" : trimmed
    }
}

struct ChatModel: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let label: String
    let isDefault: Bool

    enum CodingKeys: String, CodingKey {
        case id
        case label
        case isDefault = "is_default"
    }
}

struct ChatModelsResponse: Codable, Sendable {
    let defaultModel: String
    let models: [ChatModel]

    enum CodingKeys: String, CodingKey {
        case defaultModel = "default"
        case models
    }
}

struct CreateConversationBody: Encodable, Sendable {
    var title: String? = nil
    var folderId: UUID? = nil

    enum CodingKeys: String, CodingKey {
        case title
        case folderId = "folder_id"
    }
}

struct CreateConversationResponse: Codable, Sendable {
    let id: UUID
    let title: String?
    let folderId: UUID?

    enum CodingKeys: String, CodingKey {
        case id
        case title
        case folderId = "folder_id"
    }
}

struct UpdateConversationBody: Encodable, Sendable {
    var title: String? = nil
    var folderId: UUID? = nil
    var clearFolder: Bool = false

    enum CodingKeys: String, CodingKey {
        case title
        case folderId = "folder_id"
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        if let title {
            try container.encode(title, forKey: .title)
        }
        if clearFolder {
            try container.encodeNil(forKey: .folderId)
        } else if let folderId {
            try container.encode(folderId, forKey: .folderId)
        }
    }
}

struct MessagesResponse: Codable, Sendable {
    let messages: [ChatMessage]
}

struct SendMessageBody: Encodable, Sendable {
    let text: String
    var attachmentIds: [UUID]? = nil
    var model: String? = nil
    var clientDate: String? = nil
    var clientTime: String? = nil
    var clientTimezone: String? = nil
    var clientLocation: String? = nil

    enum CodingKeys: String, CodingKey {
        case text
        case attachmentIds = "attachment_ids"
        case model
        case clientDate = "client_date"
        case clientTime = "client_time"
        case clientTimezone = "client_timezone"
        case clientLocation = "client_location"
    }
}

struct ChatFolderInsert: Encodable, Sendable {
    let name: String
    let userId: UUID

    enum CodingKeys: String, CodingKey {
        case name
        case userId = "user_id"
    }
}

struct ChatFolderRename: Encodable, Sendable {
    let name: String
}

struct PendingAttachment: Identifiable, Hashable {
    let id: UUID
    let filename: String
    let mimeType: String
    let sizeBytes: Int
    var isUploading: Bool
    var error: String?
}
