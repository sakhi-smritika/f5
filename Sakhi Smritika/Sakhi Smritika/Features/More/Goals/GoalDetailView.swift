import SwiftUI

struct GoalDetailView: View {
    let goalId: UUID

    @Environment(AuthService.self) private var authService
    @Environment(\.dismiss) private var dismiss
    @State private var viewModel: GoalDetailViewModel?
    @State private var showDeleteConfirm = false

    var body: some View {
        Group {
            if let viewModel {
                detailContent(viewModel)
            } else {
                LoadingView()
            }
        }
        .navigationTitle("Goal")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button(role: .destructive) {
                    showDeleteConfirm = true
                } label: {
                    Image(systemName: "trash")
                }
                .accessibilityLabel("Delete goal")
            }
        }
        .confirmationDialog(
            "Delete this goal and its children?",
            isPresented: $showDeleteConfirm,
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                Task {
                    await viewModel?.delete()
                    if viewModel?.didDelete == true {
                        dismiss()
                    }
                }
            }
            Button("Cancel", role: .cancel) {}
        }
        .task {
            if viewModel == nil {
                viewModel = GoalDetailViewModel(goalId: goalId, authService: authService)
            }
            await viewModel?.load()
        }
    }

    @ViewBuilder
    private func detailContent(_ vm: GoalDetailViewModel) -> some View {
        @Bindable var vm = vm

        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                if vm.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                } else if let loadError = vm.loadError {
                    Text(loadError)
                        .font(.footnote)
                        .foregroundStyle(.red)
                } else {
                    if vm.breadcrumb.count > 1 {
                        breadcrumbBar(vm.breadcrumb)
                    }

                    field("Name") {
                        TextField("Goal name", text: $vm.goalName)
                            .padding(14)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .onChange(of: vm.goalName) { _, _ in vm.markEdited() }
                    }

                    field("Description") {
                        TextField("What does this goal mean?", text: $vm.goalDescription, axis: .vertical)
                            .lineLimit(3...8)
                            .padding(14)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .onChange(of: vm.goalDescription) { _, _ in vm.markEdited() }
                    }

                    field("Progress") {
                        TextField("Where are you with this?", text: $vm.progress, axis: .vertical)
                            .lineLimit(2...6)
                            .padding(14)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .onChange(of: vm.progress) { _, _ in vm.markEdited() }
                    }

                    if case .error(let message) = vm.saveStatus {
                        Text(message).font(.footnote).foregroundStyle(.red)
                    }

                    SaveButton(status: vm.saveStatus) {
                        Task { await vm.save() }
                    }

                    Divider().padding(.vertical, 4)

                    HStack {
                        Text("Child goals")
                            .font(.headline)
                        Spacer()
                        Button {
                            vm.showCreateChild.toggle()
                            vm.createChildStatus = .idle
                        } label: {
                            Image(systemName: "plus.circle")
                        }
                        .accessibilityLabel("Add child goal")
                    }

                    if vm.showCreateChild {
                        VStack(alignment: .leading, spacing: 10) {
                            TextField("Name", text: $vm.childName)
                                .padding(12)
                                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                            TextField("Description", text: $vm.childDescription, axis: .vertical)
                                .lineLimit(2...5)
                                .padding(12)
                                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 12, style: .continuous))
                            if case .error(let message) = vm.createChildStatus {
                                Text(message).font(.footnote).foregroundStyle(.red)
                            }
                            Button("Create child") {
                                Task { await vm.createChild() }
                            }
                            .buttonStyle(.borderedProminent)
                            .disabled(vm.createChildStatus == .saving)
                        }
                        .padding(14)
                        .background(.background, in: RoundedRectangle(cornerRadius: 16, style: .continuous))
                    }

                    if vm.children.isEmpty {
                        Text("No child goals yet.")
                            .font(.subheadline)
                            .foregroundStyle(.secondary)
                    } else {
                        ForEach(vm.children) { child in
                            NavigationLink(value: child.id) {
                                HStack {
                                    Text(child.goalName)
                                        .foregroundStyle(.primary)
                                    Spacer()
                                    Image(systemName: "chevron.right")
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.tertiary)
                                }
                                .padding(14)
                                .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                            }
                            .buttonStyle(.plain)
                        }
                    }
                }
            }
            .padding(20)
        }
        .scrollDismissesKeyboard(.interactively)
        .background(Color(.systemGroupedBackground))
    }

    private func breadcrumbBar(_ trail: [Goal]) -> some View {
        ScrollView(.horizontal, showsIndicators: false) {
            HStack(spacing: 6) {
                ForEach(Array(trail.enumerated()), id: \.element.id) { index, goal in
                    if index > 0 {
                        Image(systemName: "chevron.right")
                            .font(.caption2.weight(.bold))
                            .foregroundStyle(.tertiary)
                    }
                    if goal.id == goalId {
                        Text(goal.goalName)
                            .font(.caption.weight(.semibold))
                            .foregroundStyle(.primary)
                    } else {
                        NavigationLink(value: goal.id) {
                            Text(goal.goalName)
                                .font(.caption.weight(.semibold))
                        }
                        .buttonStyle(.plain)
                    }
                }
            }
        }
        .padding(.vertical, 4)
    }

    private func field<Content: View>(_ title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.secondary)
            content()
        }
    }
}
