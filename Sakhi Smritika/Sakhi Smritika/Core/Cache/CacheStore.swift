import Foundation
import SwiftData

/// Distinguishes "nothing cached yet" (`nil`) from "cached, and the server has
/// nothing here" (`.missing`).
enum CachedValue<Wrapped> {
    case missing
    case present(Wrapped)

    var value: Wrapped? {
        if case .present(let wrapped) = self { return wrapped }
        return nil
    }
}

/// On-disk cache backing every screen except the Kbits feed.
///
/// Reads are synchronous so view models can hydrate before their first render.
/// Every operation swallows its errors: a broken cache degrades to a network
/// fetch, it never surfaces as a user-facing failure.
@MainActor
final class CacheStore {
    private static let ownerKey = "f5-cache-owner"

    private let context: ModelContext?

    init() {
        let schema = Schema([
            CachedSyncMarker.self,
            CachedConversation.self,
            CachedMessage.self,
            CachedChatFolder.self,
            CachedChatModel.self,
            CachedKbitDiscussion.self,
            CachedKbit.self,
            CachedGoal.self,
            CachedDiaryEntry.self,
            CachedProfile.self,
            CachedGoogleStatus.self,
        ])

        let container: ModelContainer?
        do {
            container = try ModelContainer(for: schema)
        } catch {
            // A schema change or corrupt store must not brick the app; fall back
            // to a throwaway in-memory store so every read simply misses.
            container = try? ModelContainer(
                for: schema,
                configurations: ModelConfiguration(schema: schema, isStoredInMemoryOnly: true)
            )
        }
        self.context = container.map { ModelContext($0) }
    }

    // MARK: - Ownership

    /// Wipes the cache when a different user signs in on the same device.
    func ensureOwner(userId: UUID) {
        let stored = UserDefaults.standard.string(forKey: Self.ownerKey)
        guard stored != userId.uuidString else { return }
        clearAll()
        UserDefaults.standard.set(userId.uuidString, forKey: Self.ownerKey)
    }

    func clearAll() {
        write { context in
            try context.delete(model: CachedSyncMarker.self)
            try context.delete(model: CachedMessage.self)
            try context.delete(model: CachedConversation.self)
            try context.delete(model: CachedChatFolder.self)
            try context.delete(model: CachedChatModel.self)
            try context.delete(model: CachedKbitDiscussion.self)
            try context.delete(model: CachedKbit.self)
            try context.delete(model: CachedGoal.self)
            try context.delete(model: CachedDiaryEntry.self)
            try context.delete(model: CachedProfile.self)
            try context.delete(model: CachedGoogleStatus.self)
        }
        UserDefaults.standard.removeObject(forKey: Self.ownerKey)
    }

    // MARK: - Sync markers

    func hasSynced(_ key: String) -> Bool {
        fetch(
            FetchDescriptor<CachedSyncMarker>(predicate: #Predicate { $0.key == key })
        )?.isEmpty == false
    }

    func markSynced(_ key: String) {
        write { context in
            let rows = try context.fetch(
                FetchDescriptor<CachedSyncMarker>(predicate: #Predicate { $0.key == key })
            )
            if let row = rows.first {
                row.syncedAt = Date()
            } else {
                context.insert(CachedSyncMarker(key: key))
            }
        }
    }

    // MARK: - Conversations

    func conversations() -> [Conversation] {
        let rows = fetch(
            FetchDescriptor<CachedConversation>(
                sortBy: [SortDescriptor(\CachedConversation.updatedAt, order: .reverse)]
            )
        ) ?? []
        return rows.filter { $0.isListed }.map(Self.conversation(from:))
    }

    func replaceConversations(_ conversations: [Conversation]) {
        write { context in
            let existing = try context.fetch(FetchDescriptor<CachedConversation>())
            let byId = Dictionary(existing.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
            let incoming = Set(conversations.map(\.id))

            for row in existing where row.isListed && !incoming.contains(row.id) {
                context.delete(row)
            }
            for conversation in conversations {
                if let row = byId[conversation.id] {
                    Self.apply(conversation, to: row)
                } else {
                    context.insert(Self.makeRow(conversation))
                }
            }
        }
    }

    func upsertConversation(_ conversation: Conversation) {
        write { context in
            if let row = try Self.conversationRow(id: conversation.id, in: context) {
                Self.apply(conversation, to: row)
            } else {
                context.insert(Self.makeRow(conversation))
            }
        }
    }

    /// Applies only the fields that are present, matching the merge behaviour of
    /// the in-memory list so a streamed title update cannot blank out a folder.
    func mergeConversation(_ conversation: Conversation) {
        write { context in
            guard let row = try Self.conversationRow(id: conversation.id, in: context) else {
                context.insert(Self.makeRow(conversation))
                return
            }
            if let title = conversation.title { row.title = title }
            if let updatedAt = conversation.updatedAt { row.updatedAt = updatedAt }
            if let folderId = conversation.folderId { row.folderId = folderId }
            if let kbitId = conversation.kbitId { row.kbitId = kbitId }
            row.isListed = true
        }
    }

    func setConversationFolder(id: UUID, folderId: UUID?) {
        write { context in
            guard let row = try Self.conversationRow(id: id, in: context) else { return }
            row.folderId = folderId
        }
    }

    func setConversationTitle(id: UUID, title: String) {
        write { context in
            guard let row = try Self.conversationRow(id: id, in: context) else { return }
            row.title = title
        }
    }

    func deleteConversation(id: UUID) {
        write { context in
            if let row = try Self.conversationRow(id: id, in: context) {
                context.delete(row)
            }
        }
    }

    func deleteConversations(folderId: UUID) {
        write { context in
            let rows = try context.fetch(FetchDescriptor<CachedConversation>())
            for row in rows where row.folderId == folderId {
                context.delete(row)
            }
        }
    }

    // MARK: - Messages

    /// `nil` when this thread has never been fetched, which is what keeps a
    /// genuinely empty conversation from looking like a cache miss.
    func messages(conversationId: UUID) -> [ChatMessage]? {
        guard let rows = fetch(
            FetchDescriptor<CachedConversation>(
                predicate: #Predicate { $0.id == conversationId }
            )
        ), let row = rows.first, row.messagesSyncedAt != nil else { return nil }

        return row.messages
            .sorted { $0.sortIndex < $1.sortIndex }
            .map(Self.message(from:))
    }

    func replaceMessages(_ messages: [ChatMessage], conversationId: UUID) {
        write { context in
            let row: CachedConversation
            if let existing = try Self.conversationRow(id: conversationId, in: context) {
                row = existing
            } else {
                row = CachedConversation(id: conversationId)
                context.insert(row)
            }

            for message in row.messages {
                context.delete(message)
            }
            row.messages = []

            for (index, message) in messages.enumerated() {
                let steps: [ToolStepCache]? = message.toolSteps?.map { ToolStepCache(step: $0) }
                let cached = CachedMessage(
                    sortIndex: index,
                    roleRaw: message.role.rawValue,
                    text: message.text,
                    eventId: message.eventId,
                    attachmentsData: Self.encode(message.attachments),
                    toolStepsData: Self.encode(steps)
                )
                context.insert(cached)
                cached.conversation = row
            }
            row.messagesSyncedAt = Date()
        }
    }

    // MARK: - Folders

    func folders() -> [ChatFolder] {
        let rows = fetch(
            FetchDescriptor<CachedChatFolder>(sortBy: [SortDescriptor(\CachedChatFolder.name)])
        ) ?? []
        return rows.map {
            ChatFolder(id: $0.id, name: $0.name, createdAt: $0.createdAt, updatedAt: $0.updatedAt)
        }
    }

    func replaceFolders(_ folders: [ChatFolder]) {
        write { context in
            let existing = try context.fetch(FetchDescriptor<CachedChatFolder>())
            let byId = Dictionary(existing.map { ($0.id, $0) }, uniquingKeysWith: { first, _ in first })
            let incoming = Set(folders.map(\.id))

            for row in existing where !incoming.contains(row.id) {
                context.delete(row)
            }
            for folder in folders {
                if let row = byId[folder.id] {
                    row.name = folder.name
                    row.createdAt = folder.createdAt
                    row.updatedAt = folder.updatedAt
                } else {
                    context.insert(
                        CachedChatFolder(
                            id: folder.id,
                            name: folder.name,
                            createdAt: folder.createdAt,
                            updatedAt: folder.updatedAt
                        )
                    )
                }
            }
        }
    }

    func upsertFolder(_ folder: ChatFolder) {
        write { context in
            let id = folder.id
            let rows = try context.fetch(
                FetchDescriptor<CachedChatFolder>(predicate: #Predicate { $0.id == id })
            )
            if let row = rows.first {
                row.name = folder.name
                row.createdAt = folder.createdAt
                row.updatedAt = folder.updatedAt
            } else {
                context.insert(
                    CachedChatFolder(
                        id: folder.id,
                        name: folder.name,
                        createdAt: folder.createdAt,
                        updatedAt: folder.updatedAt
                    )
                )
            }
        }
    }

    func deleteFolder(id: UUID) {
        write { context in
            let rows = try context.fetch(
                FetchDescriptor<CachedChatFolder>(predicate: #Predicate { $0.id == id })
            )
            for row in rows {
                context.delete(row)
            }
        }
    }

    // MARK: - Chat models

    func chatModels() -> ChatModelsResponse? {
        guard let rows = fetch(
            FetchDescriptor<CachedChatModel>(sortBy: [SortDescriptor(\CachedChatModel.sortIndex)])
        ), !rows.isEmpty else { return nil }

        let models = rows.map { ChatModel(id: $0.id, label: $0.label, isDefault: $0.isDefault) }
        let defaultModel = rows.first { $0.isServerDefault }?.id ?? models.first?.id ?? ""
        return ChatModelsResponse(defaultModel: defaultModel, models: models)
    }

    func setChatModels(_ response: ChatModelsResponse) {
        write { context in
            try context.delete(model: CachedChatModel.self)
            for (index, model) in response.models.enumerated() {
                context.insert(
                    CachedChatModel(
                        id: model.id,
                        label: model.label,
                        isDefault: model.isDefault,
                        isServerDefault: model.id == response.defaultModel,
                        sortIndex: index
                    )
                )
            }
        }
    }

    // MARK: - Kbit discussions

    func kbitDiscussionConversationId(kbitId: UUID) -> UUID? {
        fetch(
            FetchDescriptor<CachedKbitDiscussion>(predicate: #Predicate { $0.kbitId == kbitId })
        )?.first?.conversationId
    }

    /// Drops the mapping when its conversation goes away, so a deleted discussion
    /// does not keep resolving to a conversation that no longer exists.
    func deleteKbitDiscussion(conversationId: UUID) {
        write { context in
            let rows = try context.fetch(
                FetchDescriptor<CachedKbitDiscussion>(
                    predicate: #Predicate { $0.conversationId == conversationId }
                )
            )
            for row in rows {
                context.delete(row)
            }
        }
    }

    func setKbitDiscussion(kbitId: UUID, conversationId: UUID) {
        write { context in
            let rows = try context.fetch(
                FetchDescriptor<CachedKbitDiscussion>(predicate: #Predicate { $0.kbitId == kbitId })
            )
            if let row = rows.first {
                row.conversationId = conversationId
            } else {
                context.insert(CachedKbitDiscussion(kbitId: kbitId, conversationId: conversationId))
            }
        }
    }

    // MARK: - Pinned knowledge bits

    func kbit(id: UUID) -> KnowledgeBit? {
        guard let rows = fetch(
            FetchDescriptor<CachedKbit>(predicate: #Predicate { $0.id == id })
        ), let row = rows.first else { return nil }
        return Self.kbit(from: row)
    }

    func setKbit(_ bit: KnowledgeBit) {
        write { context in
            let id = bit.id
            let rows = try context.fetch(
                FetchDescriptor<CachedKbit>(predicate: #Predicate { $0.id == id })
            )
            for row in rows {
                context.delete(row)
            }
            context.insert(
                CachedKbit(
                    id: bit.id,
                    title: bit.title,
                    content: bit.content,
                    createdAt: bit.createdAt,
                    updatedAt: bit.updatedAt,
                    relatedGoal: bit.relatedGoal,
                    generatorPrompt: bit.generatorPrompt,
                    position: bit.position,
                    isRead: bit.isRead,
                    isViewed: bit.isViewed,
                    isLiked: bit.isLiked,
                    isDisliked: bit.isDisliked,
                    rating: bit.rating,
                    isMarkedRelavant: bit.isMarkedRelavant,
                    isMarkedIrrelavant: bit.isMarkedIrrelavant
                )
            )
        }
    }

    // MARK: - Goals

    func goals() -> [Goal] {
        let rows = fetch(
            FetchDescriptor<CachedGoal>(sortBy: [SortDescriptor(\CachedGoal.sortIndex)])
        ) ?? []
        return rows.map(Self.goal(from:))
    }

    func replaceGoals(_ goals: [Goal]) {
        write { context in
            try context.delete(model: CachedGoal.self)
            for (index, goal) in goals.enumerated() {
                context.insert(
                    CachedGoal(
                        id: goal.id,
                        goalName: goal.goalName,
                        goalDescription: goal.goalDescription,
                        progress: goal.progress,
                        parentGoal: goal.parentGoal,
                        userId: goal.userId,
                        createdAt: goal.createdAt,
                        updatedAt: goal.updatedAt,
                        sortIndex: index
                    )
                )
            }
        }
    }

    func upsertGoal(_ goal: Goal) {
        write { context in
            let id = goal.id
            let rows = try context.fetch(
                FetchDescriptor<CachedGoal>(predicate: #Predicate { $0.id == id })
            )
            if let row = rows.first {
                row.goalName = goal.goalName
                row.goalDescription = goal.goalDescription
                row.progress = goal.progress
                row.parentGoal = goal.parentGoal
                row.updatedAt = goal.updatedAt
            } else {
                let count = try context.fetchCount(FetchDescriptor<CachedGoal>())
                context.insert(
                    CachedGoal(
                        id: goal.id,
                        goalName: goal.goalName,
                        goalDescription: goal.goalDescription,
                        progress: goal.progress,
                        parentGoal: goal.parentGoal,
                        userId: goal.userId,
                        createdAt: goal.createdAt,
                        updatedAt: goal.updatedAt,
                        sortIndex: count
                    )
                )
            }
        }
    }

    func deleteGoal(id: UUID) {
        write { context in
            let rows = try context.fetch(
                FetchDescriptor<CachedGoal>(predicate: #Predicate { $0.id == id })
            )
            for row in rows {
                context.delete(row)
            }
        }
    }

    // MARK: - Diary / Day Log

    func diaryEntry(date: String) -> CachedValue<DiaryEntry>? {
        guard let rows = fetch(
            FetchDescriptor<CachedDiaryEntry>(predicate: #Predicate { $0.date == date })
        ), let row = rows.first else { return nil }

        guard row.entryExists, let id = row.entryId, let userId = row.userId else {
            return .missing
        }
        return .present(
            DiaryEntry(
                id: id,
                date: row.date,
                howWasTheDay: row.howWasTheDay,
                majorEvents: row.majorEvents,
                generalContent: row.generalContent,
                dayLog: row.dayLog,
                nutritionEntries: row.nutritionEntries,
                createdAt: row.createdAt,
                updatedAt: row.updatedAt,
                userId: userId
            )
        )
    }

    func setDiaryEntry(_ entry: DiaryEntry?, date: String) {
        write { context in
            let rows = try context.fetch(
                FetchDescriptor<CachedDiaryEntry>(predicate: #Predicate { $0.date == date })
            )
            let row: CachedDiaryEntry
            if let existing = rows.first {
                row = existing
            } else {
                row = CachedDiaryEntry(date: date, entryExists: false)
                context.insert(row)
            }

            guard let entry else {
                row.entryExists = false
                row.entryId = nil
                row.userId = nil
                row.howWasTheDay = nil
                row.majorEvents = nil
                row.generalContent = nil
                row.dayLog = nil
                row.nutritionEntries = nil
                return
            }

            row.entryExists = true
            row.entryId = entry.id
            row.userId = entry.userId
            row.howWasTheDay = entry.howWasTheDay
            row.majorEvents = entry.majorEvents
            row.generalContent = entry.generalContent
            row.dayLog = entry.dayLog
            row.nutritionEntries = entry.nutritionEntries
            row.createdAt = entry.createdAt
            row.updatedAt = entry.updatedAt
        }
    }

    // MARK: - Profile

    func profile(userId: UUID) -> CachedValue<Profile>? {
        guard let rows = fetch(
            FetchDescriptor<CachedProfile>(predicate: #Predicate { $0.id == userId })
        ), let row = rows.first else { return nil }

        guard row.entryExists else { return .missing }
        return .present(
            Profile(
                id: row.id,
                username: row.username,
                displayName: row.displayName,
                fullName: row.fullName,
                userInformation: row.userInformation,
                systemInstructions: row.systemInstructions,
                createdAt: row.createdAt,
                updatedAt: row.updatedAt
            )
        )
    }

    func setProfile(_ profile: Profile?, userId: UUID) {
        write { context in
            let rows = try context.fetch(
                FetchDescriptor<CachedProfile>(predicate: #Predicate { $0.id == userId })
            )
            for row in rows {
                context.delete(row)
            }
            guard let profile else {
                context.insert(CachedProfile(id: userId, entryExists: false))
                return
            }
            context.insert(
                CachedProfile(
                    id: profile.id,
                    entryExists: true,
                    username: profile.username,
                    displayName: profile.displayName,
                    fullName: profile.fullName,
                    userInformation: profile.userInformation,
                    systemInstructions: profile.systemInstructions,
                    createdAt: profile.createdAt,
                    updatedAt: profile.updatedAt
                )
            )
        }
    }

    // MARK: - Integrations

    func googleStatus() -> GoogleConnectionStatus? {
        guard let row = fetch(FetchDescriptor<CachedGoogleStatus>())?.first else { return nil }
        return GoogleConnectionStatus(
            connected: row.connected,
            googleEmail: row.googleEmail,
            connectedAt: row.connectedAt
        )
    }

    func setGoogleStatus(_ status: GoogleConnectionStatus) {
        write { context in
            try context.delete(model: CachedGoogleStatus.self)
            context.insert(
                CachedGoogleStatus(
                    connected: status.connected,
                    googleEmail: status.googleEmail,
                    connectedAt: status.connectedAt
                )
            )
        }
    }

    // MARK: - Plumbing

    private func fetch<T: PersistentModel>(_ descriptor: FetchDescriptor<T>) -> [T]? {
        guard let context else { return nil }
        return try? context.fetch(descriptor)
    }

    private func write(_ body: (ModelContext) throws -> Void) {
        guard let context else { return }
        do {
            try body(context)
            try context.save()
        } catch {
            context.rollback()
        }
    }

    private static func conversationRow(
        id: UUID,
        in context: ModelContext
    ) throws -> CachedConversation? {
        try context.fetch(
            FetchDescriptor<CachedConversation>(predicate: #Predicate { $0.id == id })
        ).first
    }

    private static func makeRow(_ conversation: Conversation) -> CachedConversation {
        let row = CachedConversation(
            id: conversation.id,
            title: conversation.title,
            folderId: conversation.folderId,
            createdAt: conversation.createdAt,
            updatedAt: conversation.updatedAt,
            kbitId: conversation.kbitId
        )
        row.isListed = true
        return row
    }

    private static func apply(_ conversation: Conversation, to row: CachedConversation) {
        row.title = conversation.title
        row.folderId = conversation.folderId
        row.createdAt = conversation.createdAt
        row.updatedAt = conversation.updatedAt
        row.kbitId = conversation.kbitId
        row.isListed = true
    }

    private static func conversation(from row: CachedConversation) -> Conversation {
        Conversation(
            id: row.id,
            title: row.title,
            folderId: row.folderId,
            createdAt: row.createdAt,
            updatedAt: row.updatedAt,
            kbitId: row.kbitId
        )
    }

    private static func message(from row: CachedMessage) -> ChatMessage {
        ChatMessage(
            role: ChatRole(rawValue: row.roleRaw) ?? .assistant,
            text: row.text,
            eventId: row.eventId,
            attachments: decode([ChatAttachment].self, from: row.attachmentsData),
            toolSteps: decode([ToolStepCache].self, from: row.toolStepsData)?.map { $0.step }
        )
    }

    private static func goal(from row: CachedGoal) -> Goal {
        Goal(
            id: row.id,
            goalName: row.goalName,
            goalDescription: row.goalDescription,
            progress: row.progress,
            parentGoal: row.parentGoal,
            userId: row.userId,
            createdAt: row.createdAt,
            updatedAt: row.updatedAt
        )
    }

    private static func kbit(from row: CachedKbit) -> KnowledgeBit {
        KnowledgeBit(
            id: row.id,
            createdAt: row.createdAt,
            updatedAt: row.updatedAt,
            title: row.title,
            content: row.content,
            relatedGoal: row.relatedGoal,
            generatorPrompt: row.generatorPrompt,
            position: row.position,
            isRead: row.isRead,
            isViewed: row.isViewed,
            isLiked: row.isLiked,
            isDisliked: row.isDisliked,
            rating: row.rating,
            isMarkedRelavant: row.isMarkedRelavant,
            isMarkedIrrelavant: row.isMarkedIrrelavant
        )
    }

    private static func encode<T: Encodable>(_ value: T?) -> Data? {
        guard let value else { return nil }
        return try? JSONEncoder().encode(value)
    }

    private static func decode<T: Decodable>(_ type: T.Type, from data: Data?) -> T? {
        guard let data else { return nil }
        return try? JSONDecoder().decode(type, from: data)
    }
}

/// `ToolStep.encode(to:)` intentionally drops the flattened `args` string, so
/// caching round-trips through this shape instead.
private struct ToolStepCache: Codable {
    let id: String
    let name: String
    let status: String
    let argsJSON: String

    init(step: ToolStep) {
        self.id = step.id
        self.name = step.name
        self.status = step.status.rawValue
        self.argsJSON = step.argsJSON
    }

    var step: ToolStep {
        ToolStep(
            id: id,
            name: name,
            status: ToolStepStatus(rawValue: status) ?? .done,
            argsJSON: argsJSON
        )
    }
}
