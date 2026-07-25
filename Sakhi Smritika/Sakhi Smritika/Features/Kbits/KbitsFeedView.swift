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
            .toolbar {
                ToolbarItemGroup(placement: .topBarTrailing) {
                    Button {
                        viewModel?.showGenerateOptions.toggle()
                    } label: {
                        Image(systemName: "slider.horizontal.3")
                    }
                    .accessibilityLabel("Generate options")

                    Button {
                        Task { await viewModel?.generate() }
                    } label: {
                        if viewModel?.isGenerating == true {
                            ProgressView()
                        } else {
                            Image(systemName: "sparkles")
                        }
                    }
                    .disabled(viewModel?.isGenerating == true)
                    .accessibilityLabel("Generate knowledge bits")
                }
            }
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
            .sheet(isPresented: Binding(
                get: { viewModel?.showGenerateOptions ?? false },
                set: { viewModel?.showGenerateOptions = $0 }
            )) {
                if let viewModel {
                    GenerateKbitsSheet(viewModel: viewModel)
                }
            }
        }
    }

    @ViewBuilder
    private func feedContent(_ vm: KbitsFeedViewModel) -> some View {
        @Bindable var vm = vm

        ZStack {
            if vm.isLoading && vm.bits.isEmpty {
                LoadingView()
            } else if let loadError = vm.loadError, vm.bits.isEmpty {
                ContentUnavailableView(
                    "Couldn't load bits",
                    systemImage: "exclamationmark.triangle",
                    description: Text(loadError)
                )
            } else if vm.bits.isEmpty {
                ContentUnavailableView(
                    "No knowledge bits yet",
                    systemImage: "sparkles",
                    description: Text("Tap sparkles to generate insights from your goals and profile.")
                )
            } else {
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
                                    vm.currentIndex = index
                                    vm.markVisible(bit)
                                }
                            )
                            .containerRelativeFrame(.vertical)
                            .id(bit.id)
                        }
                    }
                    .scrollTargetLayout()
                }
                .scrollTargetBehavior(.paging)
                .scrollIndicators(.hidden)
                .refreshable { await vm.load() }
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

struct GenerateKbitsSheet: View {
    @Bindable var viewModel: KbitsFeedViewModel
    @Environment(\.dismiss) private var dismiss

    var body: some View {
        NavigationStack {
            Form {
                Section("Count") {
                    Stepper(value: $viewModel.generateCount, in: 1...20) {
                        Text("\(viewModel.generateCount) bits")
                    }
                }

                if let catalog = viewModel.catalog {
                    strategyPicker("Query", selection: $viewModel.queryStrategy, stage: catalog.query)
                    strategyPicker("Generator", selection: $viewModel.generatorStrategy, stage: catalog.generator)
                    strategyPicker("Screen", selection: $viewModel.screenStrategy, stage: catalog.screen)
                    strategyPicker("Rank", selection: $viewModel.rankStrategy, stage: catalog.rank)
                } else {
                    Section {
                        Text("Strategy catalog unavailable — defaults will be used.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)
                    }
                }
            }
            .navigationTitle("Generate")
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Close") { dismiss() }
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Generate") {
                        Task {
                            await viewModel.generate()
                            if viewModel.generateError == nil {
                                dismiss()
                            }
                        }
                    }
                    .disabled(viewModel.isGenerating)
                }
            }
        }
        .presentationDetents([.medium, .large])
    }

    private func strategyPicker(
        _ title: String,
        selection: Binding<String>,
        stage: StageStrategies
    ) -> some View {
        Section(title) {
            Picker(title, selection: selection) {
                Text(stage.defaultStrategy.map { "Default (\($0))" } ?? "Default")
                    .tag("")
                ForEach(stage.options, id: \.self) { option in
                    Text(option).tag(option)
                }
            }
        }
    }
}
