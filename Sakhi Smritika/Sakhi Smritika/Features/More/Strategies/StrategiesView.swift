import SwiftUI

struct StrategiesView: View {
    @Environment(AppDependencies.self) private var dependencies
    @State private var viewModel: StrategiesViewModel?

    var body: some View {
        Group {
            if let viewModel {
                content(viewModel)
            } else {
                LoadingView()
            }
        }
        .navigationTitle("Strategies")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if viewModel == nil {
                viewModel = StrategiesViewModel(apiClient: dependencies.apiClient)
            }
            await viewModel?.appear()
        }
    }

    @ViewBuilder
    private func content(_ vm: StrategiesViewModel) -> some View {
        List {
            if vm.isLoading {
                Section { ProgressView() }
            } else if let loadError = vm.loadError {
                Section {
                    Text(loadError).foregroundStyle(.red)
                }
            } else if let catalog = vm.catalog {
                strategySection(
                    title: "Query",
                    stage: "query",
                    options: catalog.query.options,
                    vm: vm
                )
                strategySection(
                    title: "Generator",
                    stage: "generator",
                    options: catalog.generator.options,
                    vm: vm
                )
                strategySection(
                    title: "Screen",
                    stage: "screen",
                    options: catalog.screen.options,
                    vm: vm
                )
                strategySection(
                    title: "Rank",
                    stage: "rank",
                    options: catalog.rank.options,
                    vm: vm
                )

                if !vm.graphs.isEmpty {
                    Section {
                        Text("Higher weight means a graph is more likely to be chosen when a graph-based query strategy runs.")
                            .font(.footnote)
                            .foregroundStyle(.secondary)

                        ForEach(vm.graphs) { graph in
                            VStack(alignment: .leading, spacing: 8) {
                                Text(graph.title)
                                    .font(.body.weight(.medium))
                                Slider(
                                    value: Binding(
                                        get: { vm.graphWeight(for: graph.id) },
                                        set: { vm.setGraphWeight(for: graph.id, value: $0) }
                                    ),
                                    in: 0...100,
                                    step: 1
                                )
                                Text("Weight: \(Int(vm.graphWeight(for: graph.id)))")
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                            }
                        }
                    } header: {
                        Text("Graph weights")
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
    }

    @ViewBuilder
    private func strategySection(
        title: String,
        stage: String,
        options: [String],
        vm: StrategiesViewModel
    ) -> some View {
        Section {
            Text("Each invoke randomly picks one strategy, weighted by these sliders.")
                .font(.footnote)
                .foregroundStyle(.secondary)

            ForEach(options, id: \.self) { strategy in
                VStack(alignment: .leading, spacing: 8) {
                    Text(strategy)
                        .font(.body.monospaced())
                    Slider(
                        value: Binding(
                            get: { vm.weight(for: stage, strategy: strategy) },
                            set: { vm.setWeight(for: stage, strategy: strategy, value: $0) }
                        ),
                        in: 0...100,
                        step: 1
                    )
                    Text("Weight: \(Int(vm.weight(for: stage, strategy: strategy)))")
                        .font(.caption)
                        .foregroundStyle(.secondary)
                }
            }
        } header: {
            Text(title)
        }
    }
}
