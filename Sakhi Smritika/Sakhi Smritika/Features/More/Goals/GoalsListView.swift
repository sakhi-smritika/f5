import SwiftUI

struct GoalsListView: View {
    @Environment(AuthService.self) private var authService
    @State private var viewModel: GoalsListViewModel?

    var body: some View {
        Group {
            if let viewModel {
                listContent(viewModel)
            } else {
                LoadingView()
            }
        }
        .navigationTitle("Goals")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    viewModel?.showCreate.toggle()
                    viewModel?.createStatus = .idle
                } label: {
                    Image(systemName: "plus.circle")
                }
                .accessibilityLabel("New goal")
            }
        }
        .navigationDestination(for: UUID.self) { goalId in
            GoalDetailView(goalId: goalId)
        }
        .task {
            if viewModel == nil {
                viewModel = GoalsListViewModel(authService: authService)
            }
            await viewModel?.load()
        }
    }

    @ViewBuilder
    private func listContent(_ vm: GoalsListViewModel) -> some View {
        @Bindable var vm = vm

        List {
            if vm.showCreate {
                Section("New goal") {
                    TextField("Name", text: $vm.newName)
                    TextField("Description", text: $vm.newDescription, axis: .vertical)
                    TextField("Progress", text: $vm.newProgress, axis: .vertical)
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
                Section {
                    ProgressView()
                }
            } else if let loadError = vm.loadError {
                Section {
                    Text(loadError).foregroundStyle(.red)
                }
            } else if vm.goals.isEmpty {
                Section {
                    ContentUnavailableView(
                        "No goals yet",
                        systemImage: "target",
                        description: Text("Tap + to add your first goal.")
                    )
                }
            } else {
                Section {
                    ForEach(vm.goals) { goal in
                        NavigationLink(value: goal.id) {
                            VStack(alignment: .leading, spacing: 4) {
                                Text(goal.goalName)
                                    .font(.body.weight(.medium))
                                if let parent = vm.parentName(for: goal) {
                                    Text("Under \(parent)")
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                } else if let progress = goal.progress, !progress.isEmpty {
                                    Text(progress)
                                        .font(.caption)
                                        .foregroundStyle(.secondary)
                                        .lineLimit(2)
                                }
                            }
                        }
                    }
                }
            }
        }
        .listStyle(.insetGrouped)
        .refreshable { await vm.load() }
    }
}
