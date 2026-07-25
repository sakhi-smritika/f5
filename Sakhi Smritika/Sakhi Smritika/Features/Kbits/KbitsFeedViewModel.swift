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

    var catalog: StrategyCatalog?
    var showGenerateOptions = false
    var generateCount = 5
    var queryStrategy = ""
    var generatorStrategy = ""
    var screenStrategy = ""
    var rankStrategy = ""

    var discussionBit: KnowledgeBit?

    private var autoReadAttempted: Set<UUID> = []
    private let apiClient: APIClient

    init(apiClient: APIClient) {
        self.apiClient = apiClient
    }

    func load() async {
        isLoading = true
        loadError = nil
        defer { isLoading = false }

        do {
            async let bitsTask = KbitService.listKbits()
            async let mapTask = KbitService.discussionMap()
            bits = try await bitsTask
            discussedKbitIds = Set((try await mapTask).keys)
            if currentIndex >= bits.count {
                currentIndex = max(0, bits.count - 1)
            }
        } catch {
            loadError = error.localizedDescription
        }

        if catalog == nil {
            catalog = try? await KbitService.strategies(api: apiClient)
        }
    }

    func generate() async {
        isGenerating = true
        generateError = nil
        defer { isGenerating = false }

        var body = InvokeKbitsBody(count: generateCount)
        body.queryStrategy = queryStrategy.nilIfEmpty
        body.generatorStrategy = generatorStrategy.nilIfEmpty
        body.screenStrategy = screenStrategy.nilIfEmpty
        body.rankStrategy = rankStrategy.nilIfEmpty

        do {
            let created = try await KbitService.invoke(api: apiClient, body: body)
            if created.isEmpty {
                generateError = "No new bits were generated."
            } else {
                bits.insert(contentsOf: created, at: 0)
                currentIndex = 0
                showGenerateOptions = false
            }
        } catch {
            generateError = error.localizedDescription
        }
    }

    func markVisible(_ bit: KnowledgeBit) {
        guard !bit.isRead, !autoReadAttempted.contains(bit.id) else { return }
        autoReadAttempted.insert(bit.id)
        Task {
            patch(bit.id) { $0.isRead = true }
            try? await KbitService.updateKbit(id: bit.id, updates: KbitUpdate(isRead: true))
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
        Task {
            do {
                try await KbitService.delete(api: apiClient, id: bit.id)
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

    private func patch(_ id: UUID, _ mutate: (inout KnowledgeBit) -> Void) {
        guard let index = bits.firstIndex(where: { $0.id == id }) else { return }
        mutate(&bits[index])
    }
}

private extension String {
    var nilIfEmpty: String? {
        trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : self
    }
}
