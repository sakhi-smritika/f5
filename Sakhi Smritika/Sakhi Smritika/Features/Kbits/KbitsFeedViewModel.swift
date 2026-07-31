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
    var isRefreshing = false
    var loadError: String?
    var generateError: String?

    var discussionBit: KnowledgeBit?

    private var autoViewAttempted: Set<UUID> = []
    private let apiClient: APIClient

    init(apiClient: APIClient) {
        self.apiClient = apiClient
    }

    func load() async {
        isLoading = true
        loadError = nil
        defer { isLoading = false }

        do {
            async let bitsTask = KbitService.listKbits(unviewedOnly: true)
            async let mapTask = KbitService.discussionMap()
            bits = try await bitsTask
            discussedKbitIds = Set((try await mapTask).keys)
            currentIndex = min(currentIndex, max(0, bits.count - 1))
        } catch {
            loadError = error.localizedDescription
        }
    }

    /// Reload unviewed bits from Supabase, preserving in-memory edits for rows still in the feed.
    func refresh() async {
        guard !isRefreshing else { return }
        isRefreshing = true
        generateError = nil
        defer { isRefreshing = false }

        do {
            async let bitsTask = KbitService.listKbits(unviewedOnly: true)
            async let mapTask = KbitService.discussionMap()
            let fetched = try await bitsTask
            discussedKbitIds = Set((try await mapTask).keys)

            let localById = Dictionary(uniqueKeysWithValues: bits.map { ($0.id, $0) })
            bits = fetched
                .sorted { $0.position < $1.position }
                .map { localById[$0.id] ?? $0 }
            currentIndex = min(currentIndex, max(0, bits.count - 1))

            if bits.isEmpty {
                generateError = "No unviewed bits for your account. Swiping past a card marks it viewed."
            }
        } catch {
            generateError = error.localizedDescription
        }
    }

    func onCardVisible(at index: Int, bit: KnowledgeBit) {
        if index > currentIndex {
            markViewed(bitAt: currentIndex)
        }
        currentIndex = index
    }

    func onActionCardVisible() {
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

    /// Start generation on the backend. Completes in the background; use Refresh if the request times out.
    func invokeMore() {
        guard !isGenerating else { return }
        Task { await runInvoke() }
    }

    private func runInvoke() async {
        isGenerating = true
        generateError = nil
        defer { isGenerating = false }

        do {
            let preferences = StrategyPreferencesStore.shared
            async let catalogTask = KbitService.strategies(api: apiClient)
            async let graphsTask = KnowledgeGraphService.listGraphs()
            let catalog = try await catalogTask
            let graphs = try await graphsTask

            let created = try await KbitService.invoke(
                api: apiClient,
                body: InvokeKbitsBody(
                    count: 5,
                    strategyWeights: preferences.strategyWeightsPayload(catalog: catalog),
                    graphWeights: preferences.graphWeightsPayload(graphs: graphs)
                )
            )
            if created.isEmpty {
                generateError = "No new bits were generated."
            } else {
                appendNewBits(created)
                generateError = nil
            }
        } catch {
            generateError = "\(error.localizedDescription) Tap Refresh to check for new bits."
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
