import Foundation
import Observation

@MainActor
@Observable
final class KbitsFeedViewModel {
    var bits: [KnowledgeBit] = []
    var discussedKbitIds: Set<UUID> = []
    var currentIndex: Int = 0
    var isLoading = true
    var isGenerating = false
    var loadError: String?
    var generateError: String?

    var discussionBit: KnowledgeBit?

    private var autoViewAttempted: Set<UUID> = []
    private var invokeTriggeredForLastId: UUID?
    private let apiClient: APIClient

    init(apiClient: APIClient) {
        self.apiClient = apiClient
    }

    func load() async {
        isLoading = true
        loadError = nil
        invokeTriggeredForLastId = nil
        defer { isLoading = false }

        do {
            async let bitsTask = KbitService.listKbits(unviewedOnly: true)
            async let mapTask = KbitService.discussionMap()
            bits = try await bitsTask
            discussedKbitIds = Set((try await mapTask).keys)
            currentIndex = 0

            if bits.isEmpty {
                await invokeMore()
            }
        } catch {
            loadError = error.localizedDescription
        }
    }

    func onCardVisible(at index: Int, bit: KnowledgeBit) {
        if index > currentIndex {
            markViewed(bitAt: currentIndex)
        }
        currentIndex = index

        if index == bits.count - 1 {
            Task { await loadMoreIfNeeded(triggerBitId: bit.id) }
        }
    }

    func onLoadingCardVisible() {
        markViewed(bitAt: currentIndex)
        currentIndex = bits.count
    }

    private func markViewed(bitAt index: Int) {
        guard index >= 0, index < bits.count else { return }
        markViewed(bits[index])
    }

    private func markViewed(_ bit: KnowledgeBit) {
        guard !bit.isViewed, !autoViewAttempted.contains(bit.id) else { return }
        autoViewAttempted.insert(bit.id)
        Task {
            patch(bit.id) { $0.isViewed = true }
            try? await KbitService.updateKbit(id: bit.id, updates: KbitUpdate(isViewed: true))
        }
    }

    func loadMoreIfNeeded(triggerBitId: UUID) async {
        guard !isGenerating else { return }
        guard invokeTriggeredForLastId != triggerBitId else { return }
        invokeTriggeredForLastId = triggerBitId
        await invokeMore()
    }

    func invokeMore() async {
        isGenerating = true
        generateError = nil
        defer { isGenerating = false }

        do {
            let created = try await KbitService.invoke(
                api: apiClient,
                body: InvokeKbitsBody(count: 5)
            )
            if created.isEmpty {
                generateError = "No new bits were generated."
                invokeTriggeredForLastId = nil
            } else {
                appendNewBits(created)
            }
        } catch {
            generateError = error.localizedDescription
            invokeTriggeredForLastId = nil
        }
    }

    func toggleLike(_ bit: KnowledgeBit) {
        let nextLiked = !bit.isLiked
        Task {
            patch(bit.id) {
                $0.isLiked = nextLiked
                if nextLiked { $0.isDisliked = false }
            }
            do {
                try await KbitService.updateKbit(
                    id: bit.id,
                    updates: KbitUpdate(isLiked: nextLiked, isDisliked: nextLiked ? false : nil)
                )
            } catch {
                await load()
            }
        }
    }

    func toggleDislike(_ bit: KnowledgeBit) {
        let next = !bit.isDisliked
        Task {
            patch(bit.id) {
                $0.isDisliked = next
                if next { $0.isLiked = false }
            }
            do {
                try await KbitService.updateKbit(
                    id: bit.id,
                    updates: KbitUpdate(isLiked: next ? false : nil, isDisliked: next)
                )
            } catch {
                await load()
            }
        }
    }

    func toggleRelevant(_ bit: KnowledgeBit) {
        let next = !bit.isMarkedRelavant
        Task {
            patch(bit.id) {
                $0.isMarkedRelavant = next
                if next { $0.isMarkedIrrelavant = false }
            }
            do {
                try await KbitService.updateKbit(
                    id: bit.id,
                    updates: KbitUpdate(
                        isMarkedRelavant: next,
                        isMarkedIrrelavant: next ? false : nil
                    )
                )
            } catch {
                await load()
            }
        }
    }

    func toggleIrrelevant(_ bit: KnowledgeBit) {
        let next = !bit.isMarkedIrrelavant
        Task {
            patch(bit.id) {
                $0.isMarkedIrrelavant = next
                if next { $0.isMarkedRelavant = false }
            }
            do {
                try await KbitService.updateKbit(
                    id: bit.id,
                    updates: KbitUpdate(
                        isMarkedRelavant: next ? false : nil,
                        isMarkedIrrelavant: next
                    )
                )
            } catch {
                await load()
            }
        }
    }

    func delete(_ bit: KnowledgeBit) {
        let previous = bits
        bits.removeAll { $0.id == bit.id }
        if currentIndex >= bits.count {
            currentIndex = max(0, bits.count - 1)
        }
        invokeTriggeredForLastId = nil
        Task {
            do {
                try await KbitService.delete(api: apiClient, id: bit.id)
                if bits.isEmpty {
                    await invokeMore()
                } else if currentIndex >= bits.count - 1, let last = bits.last {
                    await loadMoreIfNeeded(triggerBitId: last.id)
                }
            } catch {
                bits = previous
                generateError = error.localizedDescription
            }
        }
    }

    func openDiscussion(_ bit: KnowledgeBit) {
        discussionBit = bit
        discussedKbitIds.insert(bit.id)
    }

    private func appendNewBits(_ created: [KnowledgeBit]) {
        let existingIds = Set(bits.map(\.id))
        let newBits = created
            .filter { !existingIds.contains($0.id) }
            .sorted { $0.position < $1.position }
        bits.append(contentsOf: newBits)
    }

    private func patch(_ id: UUID, _ mutate: (inout KnowledgeBit) -> Void) {
        guard let index = bits.firstIndex(where: { $0.id == id }) else { return }
        mutate(&bits[index])
    }
}
