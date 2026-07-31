import Foundation
import SwiftData

/// Records that a collection has been fetched at least once, so an empty list
/// reads as "you have nothing" rather than "we never looked".
@Model
final class CachedSyncMarker {
    @Attribute(.unique) var key: String
    var syncedAt: Date

    init(key: String, syncedAt: Date = Date()) {
        self.key = key
        self.syncedAt = syncedAt
    }
}

// MARK: - Chat

@Model
final class CachedConversation {
    @Attribute(.unique) var id: UUID
    var title: String?
    var folderId: UUID?
    var createdAt: String?
    var updatedAt: String?
    var kbitId: UUID?

    /// Set once this thread's messages have been fetched from the server, which
    /// distinguishes "an empty thread" from "we have never looked".
    var messagesSyncedAt: Date?

    /// `false` for rows created solely to hold cached messages, before the
    /// conversation list has caught up. Those must not show up in the sidebar
    /// as untitled chats.
    var isListed: Bool = false

    @Relationship(deleteRule: .cascade, inverse: \CachedMessage.conversation)
    var messages: [CachedMessage] = []

    init(
        id: UUID,
        title: String? = nil,
        folderId: UUID? = nil,
        createdAt: String? = nil,
        updatedAt: String? = nil,
        kbitId: UUID? = nil
    ) {
        self.id = id
        self.title = title
        self.folderId = folderId
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.kbitId = kbitId
    }
}

@Model
final class CachedMessage {
    /// The API does not send message ids, so position within the thread is the
    /// only stable identity. Threads are replaced wholesale rather than upserted.
    var sortIndex: Int
    var roleRaw: String
    var text: String
    var eventId: String?
    /// JSON-encoded `[ChatAttachment]`.
    var attachmentsData: Data?
    /// JSON-encoded tool steps, including the flattened `args` string that
    /// `ToolStep`'s own `Encodable` conformance drops.
    var toolStepsData: Data?

    var conversation: CachedConversation?

    init(
        sortIndex: Int,
        roleRaw: String,
        text: String,
        eventId: String? = nil,
        attachmentsData: Data? = nil,
        toolStepsData: Data? = nil
    ) {
        self.sortIndex = sortIndex
        self.roleRaw = roleRaw
        self.text = text
        self.eventId = eventId
        self.attachmentsData = attachmentsData
        self.toolStepsData = toolStepsData
    }
}

@Model
final class CachedChatFolder {
    @Attribute(.unique) var id: UUID
    var name: String
    var createdAt: String?
    var updatedAt: String?

    init(id: UUID, name: String, createdAt: String? = nil, updatedAt: String? = nil) {
        self.id = id
        self.name = name
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

@Model
final class CachedChatModel {
    @Attribute(.unique) var id: String
    var label: String
    var isDefault: Bool
    /// Mirrors `ChatModelsResponse.default`, which is separate from each model's
    /// own `is_default` flag.
    var isServerDefault: Bool
    var sortIndex: Int

    init(id: String, label: String, isDefault: Bool, isServerDefault: Bool, sortIndex: Int) {
        self.id = id
        self.label = label
        self.isDefault = isDefault
        self.isServerDefault = isServerDefault
        self.sortIndex = sortIndex
    }
}

/// Maps a knowledge bit to its discussion conversation so reopening a
/// discussion sheet does not need a round trip to resolve the id.
@Model
final class CachedKbitDiscussion {
    @Attribute(.unique) var kbitId: UUID
    var conversationId: UUID

    init(kbitId: UUID, conversationId: UUID) {
        self.kbitId = kbitId
        self.conversationId = conversationId
    }
}

/// Only knowledge bits pinned to a conversation are cached. The Kbits feed is
/// deliberately not cached — bits are generated continuously and not revisited.
@Model
final class CachedKbit {
    @Attribute(.unique) var id: UUID
    var title: String
    var content: String
    var createdAt: String?
    var updatedAt: String?
    var relatedGoal: UUID?
    var generatorPrompt: String?
    var position: Int
    var isRead: Bool
    var isViewed: Bool
    var isLiked: Bool
    var isDisliked: Bool
    var rating: Double?
    var isMarkedRelavant: Bool
    var isMarkedIrrelavant: Bool

    init(
        id: UUID,
        title: String,
        content: String,
        createdAt: String?,
        updatedAt: String?,
        relatedGoal: UUID?,
        generatorPrompt: String? = nil,
        position: Int,
        isRead: Bool,
        isViewed: Bool,
        isLiked: Bool,
        isDisliked: Bool,
        rating: Double?,
        isMarkedRelavant: Bool,
        isMarkedIrrelavant: Bool
    ) {
        self.id = id
        self.title = title
        self.content = content
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.relatedGoal = relatedGoal
        self.generatorPrompt = generatorPrompt
        self.position = position
        self.isRead = isRead
        self.isViewed = isViewed
        self.isLiked = isLiked
        self.isDisliked = isDisliked
        self.rating = rating
        self.isMarkedRelavant = isMarkedRelavant
        self.isMarkedIrrelavant = isMarkedIrrelavant
    }
}

// MARK: - Goals

@Model
final class CachedGoal {
    @Attribute(.unique) var id: UUID
    var goalName: String
    var goalDescription: String?
    var progress: String?
    var parentGoal: UUID?
    var userId: UUID
    var createdAt: String?
    var updatedAt: String?
    /// Preserves the server's ordering (newest first) without reparsing dates.
    var sortIndex: Int

    init(
        id: UUID,
        goalName: String,
        goalDescription: String?,
        progress: String?,
        parentGoal: UUID?,
        userId: UUID,
        createdAt: String?,
        updatedAt: String?,
        sortIndex: Int
    ) {
        self.id = id
        self.goalName = goalName
        self.goalDescription = goalDescription
        self.progress = progress
        self.parentGoal = parentGoal
        self.userId = userId
        self.createdAt = createdAt
        self.updatedAt = updatedAt
        self.sortIndex = sortIndex
    }
}

// MARK: - Diary / Day Log

/// One row per date, shared by the Diary and Day Log screens since both read
/// the same `diary` row.
@Model
final class CachedDiaryEntry {
    @Attribute(.unique) var date: String
    /// `false` records that the server has no entry for this date, which is
    /// different from having never fetched it.
    var entryExists: Bool
    var entryId: UUID?
    var userId: UUID?
    var howWasTheDay: String?
    var majorEvents: String?
    var generalContent: String?
    var dayLog: [String: String]?
    var createdAt: String?
    var updatedAt: String?

    init(
        date: String,
        entryExists: Bool,
        entryId: UUID? = nil,
        userId: UUID? = nil,
        howWasTheDay: String? = nil,
        majorEvents: String? = nil,
        generalContent: String? = nil,
        dayLog: [String: String]? = nil,
        createdAt: String? = nil,
        updatedAt: String? = nil
    ) {
        self.date = date
        self.entryExists = entryExists
        self.entryId = entryId
        self.userId = userId
        self.howWasTheDay = howWasTheDay
        self.majorEvents = majorEvents
        self.generalContent = generalContent
        self.dayLog = dayLog
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

// MARK: - Profile

@Model
final class CachedProfile {
    @Attribute(.unique) var id: UUID
    var entryExists: Bool
    var username: String?
    var displayName: String?
    var fullName: String?
    var userInformation: String?
    var systemInstructions: String?
    var createdAt: String?
    var updatedAt: String?

    init(
        id: UUID,
        entryExists: Bool,
        username: String? = nil,
        displayName: String? = nil,
        fullName: String? = nil,
        userInformation: String? = nil,
        systemInstructions: String? = nil,
        createdAt: String? = nil,
        updatedAt: String? = nil
    ) {
        self.id = id
        self.entryExists = entryExists
        self.username = username
        self.displayName = displayName
        self.fullName = fullName
        self.userInformation = userInformation
        self.systemInstructions = systemInstructions
        self.createdAt = createdAt
        self.updatedAt = updatedAt
    }
}

// MARK: - Integrations

@Model
final class CachedGoogleStatus {
    @Attribute(.unique) var key: String
    var connected: Bool
    var googleEmail: String?
    var connectedAt: String?

    init(key: String = "google", connected: Bool, googleEmail: String?, connectedAt: String?) {
        self.key = key
        self.connected = connected
        self.googleEmail = googleEmail
        self.connectedAt = connectedAt
    }
}
