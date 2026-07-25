import Foundation

enum ChatRole: String, Codable, Sendable {
    case user
    case assistant
}

enum ToolStepStatus: String, Codable, Sendable {
    case running
    case done
    case error
}

struct ToolStep: Codable, Identifiable, Hashable, Sendable {
    let id: String
    let name: String
    var status: ToolStepStatus
    var argsJSON: String

    enum CodingKeys: String, CodingKey {
        case id
        case name
        case status
        case args
    }

    init(id: String, name: String, status: ToolStepStatus, argsJSON: String = "{}") {
        self.id = id
        self.name = name
        self.status = status
        self.argsJSON = argsJSON
    }

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: CodingKeys.self)
        id = try container.decode(String.self, forKey: .id)
        name = try container.decode(String.self, forKey: .name)
        status = try container.decode(ToolStepStatus.self, forKey: .status)
        if let args = try container.decodeIfPresent(JSONDictionary.self, forKey: .args) {
            argsJSON = Self.formatArgs(args.values)
        } else {
            argsJSON = "{}"
        }
    }

    func encode(to encoder: Encoder) throws {
        var container = encoder.container(keyedBy: CodingKeys.self)
        try container.encode(id, forKey: .id)
        try container.encode(name, forKey: .name)
        try container.encode(status, forKey: .status)
    }

    static func fromSSE(_ json: [String: Any]) -> ToolStep? {
        guard let id = json["id"] as? String,
              let name = json["name"] as? String,
              let statusRaw = json["status"] as? String,
              let status = ToolStepStatus(rawValue: statusRaw)
        else { return nil }
        let args = json["args"] as? [String: Any] ?? [:]
        return ToolStep(id: id, name: name, status: status, argsJSON: formatArgs(args))
    }

    private static func formatArgs(_ args: [String: Any]) -> String {
        guard !args.isEmpty,
              JSONSerialization.isValidJSONObject(args),
              let data = try? JSONSerialization.data(
                withJSONObject: args,
                options: [.prettyPrinted, .sortedKeys]
              ),
              let string = String(data: data, encoding: .utf8)
        else { return "{}" }
        return string
    }
}

/// Decodes arbitrary JSON objects for tool argument payloads.
private struct JSONDictionary: Decodable {
    let values: [String: Any]

    init(from decoder: Decoder) throws {
        let container = try decoder.container(keyedBy: DynamicCodingKey.self)
        var result: [String: Any] = [:]
        for key in container.allKeys {
            if let value = try? container.decode(JSONAnyValue.self, forKey: key) {
                result[key.stringValue] = value.value
            }
        }
        values = result
    }
}

private struct JSONAnyValue: Decodable {
    let value: Any

    init(from decoder: Decoder) throws {
        let container = try decoder.singleValueContainer()
        if container.decodeNil() {
            value = NSNull()
        } else if let bool = try? container.decode(Bool.self) {
            value = bool
        } else if let int = try? container.decode(Int.self) {
            value = int
        } else if let double = try? container.decode(Double.self) {
            value = double
        } else if let string = try? container.decode(String.self) {
            value = string
        } else if let array = try? container.decode([JSONAnyValue].self) {
            value = array.map(\.value)
        } else if let object = try? container.decode([String: JSONAnyValue].self) {
            value = object.mapValues(\.value)
        } else {
            value = NSNull()
        }
    }
}

private struct DynamicCodingKey: CodingKey {
    var stringValue: String
    var intValue: Int?

    init?(stringValue: String) {
        self.stringValue = stringValue
    }

    init?(intValue: Int) {
        self.intValue = intValue
        self.stringValue = "\(intValue)"
    }
}

enum ChatMessageToolSteps {
    static func apply(_ step: ToolStep, to steps: [ToolStep]?) -> [ToolStep] {
        var list = steps ?? []
        if let index = list.firstIndex(where: { $0.id == step.id }) {
            var existing = list[index]
            existing.status = step.status
            if step.argsJSON != "{}" {
                existing.argsJSON = step.argsJSON
            }
            list[index] = existing
        } else {
            list.append(step)
        }
        return list
    }
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
    var toolSteps: [ToolStep]?

    enum CodingKeys: String, CodingKey {
        case role
        case text
        case eventId = "event_id"
        case attachments
        case toolSteps = "tool_steps"
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
