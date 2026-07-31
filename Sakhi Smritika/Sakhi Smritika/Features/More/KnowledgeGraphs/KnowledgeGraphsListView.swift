import SwiftUI

struct KnowledgeGraphsListView: View {
    @Environment(AuthService.self) private var authService
    @State private var viewModel: KnowledgeGraphsViewModel?

    var body: some View {
        Group {
            if let viewModel {
                listContent(viewModel)
            } else {
                LoadingView()
            }
        }
        .navigationTitle("Knowledge Graphs")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    viewModel?.showCreate.toggle()
                    viewModel?.createStatus = .idle
                } label: {
                    Image(systemName: "plus.circle")
                }
                .accessibilityLabel("New knowledge graph")
            }
        }
        .task {
            if viewModel == nil {
                viewModel = KnowledgeGraphsViewModel(authService: authService)
            }
            await viewModel?.appear()
        }
    }

    @ViewBuilder
    private func listContent(_ vm: KnowledgeGraphsViewModel) -> some View {
        @Bindable var vm = vm

        List {
            if vm.showCreate {
                Section("New graph") {
                    TextField("Title", text: $vm.newTitle)
                    TextField("Description", text: $vm.newDescription, axis: .vertical)
                    TextField("First concept node", text: $vm.newFirstNode)
                    if case .error(let message) = vm.createStatus {
                        Text(message).font(.footnote).foregroundStyle(.red)
                    }
                    Button {
                        Task { await vm.create() }
                    } label: {
                        if vm.createStatus == .saving {
                            ProgressView()
                        } else {
                            Text("Create")
                        }
                    }
                    .disabled(vm.createStatus == .saving)
                }
            }

            if vm.isLoading {
                Section { ProgressView() }
            } else if let loadError = vm.loadError {
                Section {
                    Text(loadError).foregroundStyle(.red)
                }
            } else if vm.graphs.isEmpty {
                Section {
                    ContentUnavailableView(
                        "No graphs yet",
                        systemImage: "point.3.connected.trianglepath.dotted",
                        description: Text("Tap + to seed your first learning domain.")
                    )
                }
            } else {
                Section {
                    ForEach(vm.graphs) { graph in
                        VStack(alignment: .leading, spacing: 4) {
                            Text(graph.title)
                                .font(.body.weight(.medium))
                            if let description = graph.description, !description.isEmpty {
                                Text(description)
                                    .font(.caption)
                                    .foregroundStyle(.secondary)
                                    .lineLimit(2)
                            }
                        }
                        .swipeActions {
                            Button(role: .destructive) {
                                Task { await vm.delete(graph) }
                            } label: {
                                Label("Delete", systemImage: "trash")
                            }
                        }
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .refreshable { await vm.reload() }
    }
}
