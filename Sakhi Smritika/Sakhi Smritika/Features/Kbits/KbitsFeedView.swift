import SwiftUI

struct KbitsFeedView: View {
    @Environment(AppDependencies.self) private var dependencies
    @State private var viewModel: KbitsFeedViewModel?

    var body: some View {
        NavigationStack {
            Group {
                if let viewModel {
                    feedContent(viewModel)
                } else {
                    LoadingView(message: "Loading bits…")
                }
            }
            .navigationTitle("Kbits")
            .task {
                if viewModel == nil {
                    viewModel = KbitsFeedViewModel(apiClient: dependencies.apiClient)
                }
                await viewModel?.load()
            }
            .sheet(item: Binding(
                get: { viewModel?.discussionBit },
                set: { viewModel?.discussionBit = $0 }
            )) { bit in
                KbitDiscussionSheet(bit: bit, viewModel: discussionViewModel(for: bit))
            }
        }
    }

    private func discussionViewModel(for bit: KnowledgeBit) -> ChatThreadViewModel {
        dependencies.threadRegistry.viewModel(for: .kbit(bit.id)) {
            ChatThreadViewModel(
                conversation: nil,
                models: [],
                selectedModelId: "",
                apiClient: dependencies.apiClient,
                cache: dependencies.cache,
                refreshTracker: dependencies.refreshTracker,
                bootstrapKbit: bit
            )
        }
    }

    @ViewBuilder
    private func feedContent(_ vm: KbitsFeedViewModel) -> some View {
        @Bindable var vm = vm

        ZStack {
            if vm.isLoading && vm.bits.isEmpty {
                LoadingView(message: "Loading bits…")
            } else if let loadError = vm.loadError, vm.bits.isEmpty {
                ContentUnavailableView(
                    "Couldn't load bits",
                    systemImage: "exclamationmark.triangle",
                    description: Text(loadError)
                )
            } else {
                GeometryReader { geo in
                    ScrollView(.vertical) {
                        LazyVStack(spacing: 0) {
                            ForEach(Array(vm.bits.enumerated()), id: \.element.id) { index, bit in
                                KbitCardView(
                                    bit: bit,
                                    hasDiscussion: vm.discussedKbitIds.contains(bit.id),
                                    onLike: { vm.toggleLike(bit) },
                                    onDislike: { vm.toggleDislike(bit) },
                                    onRelevant: { vm.toggleRelevant(bit) },
                                    onIrrelevant: { vm.toggleIrrelevant(bit) },
                                    onDiscuss: { vm.openDiscussion(bit) },
                                    onDelete: { vm.delete(bit) },
                                    onBecameVisible: {
                                        vm.onCardVisible(at: index, bit: bit)
                                    }
                                )
                                .frame(width: geo.size.width, height: geo.size.height)
                                .id(bit.id)
                            }

                            KbitActionCardView(
                                isGenerating: vm.isGenerating,
                                isRefreshing: vm.isRefreshing,
                                onInvoke: { vm.invokeMore() },
                                onRefresh: { Task { await vm.refresh() } },
                                onBecameVisible: { vm.onActionCardVisible() }
                            )
                            .frame(width: geo.size.width, height: geo.size.height)
                            .id("action")
                        }
                        .scrollTargetLayout()
                    }
                    .scrollTargetBehavior(.paging)
                    .scrollIndicators(.hidden)
                    .refreshable { await vm.refresh() }
                }
            }

            if let generateError = vm.generateError {
                VStack {
                    Text(generateError)
                        .font(.footnote)
                        .foregroundStyle(.red)
                        .padding(10)
                        .background(.ultraThinMaterial, in: RoundedRectangle(cornerRadius: 12))
                        .padding()
                    Spacer()
                }
            }
        }
    }
}
