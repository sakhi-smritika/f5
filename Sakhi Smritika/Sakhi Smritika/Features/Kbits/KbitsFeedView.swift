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
                KbitDiscussionSheet(bit: bit, apiClient: dependencies.apiClient)
            }
        }
    }

    @ViewBuilder
    private func feedContent(_ vm: KbitsFeedViewModel) -> some View {
        @Bindable var vm = vm

        ZStack {
            if vm.isLoading && vm.bits.isEmpty {
                LoadingView(message: vm.isGenerating ? "Finding new bits…" : "Loading bits…")
            } else if let loadError = vm.loadError, vm.bits.isEmpty, !vm.isGenerating {
                ContentUnavailableView(
                    "Couldn't load bits",
                    systemImage: "exclamationmark.triangle",
                    description: Text(loadError)
                )
            } else if vm.bits.isEmpty && !vm.isGenerating {
                ContentUnavailableView(
                    "No new bits right now",
                    systemImage: "sparkles",
                    description: Text("Pull down to refresh, or check back later.")
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

                            if vm.isGenerating {
                                KbitLoadingCardView()
                                    .frame(width: geo.size.width, height: geo.size.height)
                                    .id("loading")
                                    .onAppear { vm.onLoadingCardVisible() }
                            }
                        }
                        .scrollTargetLayout()
                    }
                    .scrollTargetBehavior(.paging)
                    .scrollIndicators(.hidden)
                    .refreshable { await vm.load() }
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

private struct KbitLoadingCardView: View {
    var body: some View {
        VStack(spacing: 16) {
            ProgressView()
            Text("Loading more bits…")
                .font(.subheadline)
                .foregroundStyle(.secondary)
        }
        .frame(maxWidth: .infinity, maxHeight: .infinity)
        .padding(.horizontal, 16)
        .padding(.vertical, 10)
    }
}
