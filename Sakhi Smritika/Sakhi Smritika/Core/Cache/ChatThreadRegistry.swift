import Foundation

/// Keeps thread view models alive across navigation.
///
/// The on-disk cache restores messages, but a draft in the composer, uploaded
/// attachments, and an in-flight stream only exist in memory — so reopening a
/// conversation has to hand back the same instance, not a rebuilt one.
///
/// Shared app-wide because a knowledge bit discussion and the chat list can
/// both land on the same conversation.
@MainActor
final class ChatThreadRegistry {
    enum Key: Hashable {
        case draft(UUID)
        case conversation(UUID)
        case kbit(UUID)
    }

    /// Bounded so a long session cannot pin every thread it opened in memory.
    private let limit = 8

    private var viewModels: [Key: ChatThreadViewModel] = [:]
    private var recentKeys: [Key] = []

    func viewModel(for key: Key, make: () -> ChatThreadViewModel) -> ChatThreadViewModel {
        if let existing = viewModels[key] {
            touch(key)
            return existing
        }

        // The same thread can be reached under more than one key: a draft that has
        // since created its conversation, or a discussion opened from both the
        // Kbits feed and the chat list. Reuse the live instance rather than
        // running a second one against the same conversation.
        if let (previousKey, existing) = equivalent(to: key) {
            viewModels.removeValue(forKey: previousKey)
            recentKeys.removeAll { $0 == previousKey }
            viewModels[key] = existing
            touch(key)
            return existing
        }

        let created = make()
        viewModels[key] = created
        touch(key)
        return created
    }

    private func equivalent(to key: Key) -> (Key, ChatThreadViewModel)? {
        switch key {
        case .conversation(let id):
            for (existingKey, viewModel) in viewModels where viewModel.conversationId == id {
                return (existingKey, viewModel)
            }
        case .kbit(let id):
            for (existingKey, viewModel) in viewModels where viewModel.kbitId == id {
                return (existingKey, viewModel)
            }
        case .draft:
            return nil
        }
        return nil
    }

    func remove(conversationId: UUID) {
        for (key, viewModel) in viewModels where viewModel.conversationId == conversationId {
            viewModels.removeValue(forKey: key)
            recentKeys.removeAll { $0 == key }
        }
    }

    func removeAll() {
        viewModels.removeAll()
        recentKeys.removeAll()
    }

    private func touch(_ key: Key) {
        recentKeys.removeAll { $0 == key }
        recentKeys.append(key)

        while recentKeys.count > limit {
            // Never evict a thread that is mid-stream.
            guard let index = recentKeys.firstIndex(where: { viewModels[$0]?.isStreaming != true })
            else { return }
            let evicted = recentKeys.remove(at: index)
            viewModels.removeValue(forKey: evicted)
        }
    }
}
