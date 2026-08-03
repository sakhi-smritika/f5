import SwiftUI

struct NutritionTemplatesListView: View {
    @Environment(AuthService.self) private var authService
    @State private var viewModel: NutritionTemplatesViewModel?

    var body: some View {
        Group {
            if let viewModel {
                listContent(viewModel)
            } else {
                LoadingView()
            }
        }
        .navigationTitle("Nutrition Templates")
        .navigationBarTitleDisplayMode(.inline)
        .toolbar {
            ToolbarItem(placement: .topBarTrailing) {
                Button {
                    viewModel?.showCreate.toggle()
                    viewModel?.createStatus = .idle
                } label: {
                    Image(systemName: "plus.circle")
                }
                .accessibilityLabel("New template")
            }
        }
        .task {
            if viewModel == nil {
                viewModel = NutritionTemplatesViewModel(authService: authService)
            }
            await viewModel?.appear()
        }
    }

    @ViewBuilder
    private func listContent(_ vm: NutritionTemplatesViewModel) -> some View {
        @Bindable var vm = vm

        List {
            if vm.showCreate {
                Section("New template") {
                    Picker("Hour", selection: $vm.newHour) {
                        ForEach(0..<24, id: \.self) { hour in
                            Text(DayLogViewModel.hourLabel(hour)).tag(hour)
                        }
                    }
                    TextField("What you usually eat", text: $vm.newNutrition, axis: .vertical)
                        .lineLimit(2...4)
                    Toggle("Active", isOn: $vm.newIsActive)
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
            } else if vm.templates.isEmpty {
                Section {
                    ContentUnavailableView(
                        "No templates",
                        systemImage: "fork.knife",
                        description: Text("Create presets to swipe into your day log.")
                    )
                }
            } else {
                Section {
                    ForEach(vm.templates) { template in
                        Button {
                            vm.beginEdit(template)
                        } label: {
                            VStack(alignment: .leading, spacing: 4) {
                                HStack {
                                    Text(DayLogViewModel.hourLabel(template.hour))
                                        .font(.caption.weight(.semibold))
                                        .foregroundStyle(.secondary)
                                    if !template.isActive {
                                        Text("Inactive")
                                            .font(.caption2.weight(.semibold))
                                            .padding(.horizontal, 6)
                                            .padding(.vertical, 2)
                                            .background(Color.secondary.opacity(0.15), in: Capsule())
                                    }
                                }
                                Text(template.nutrition)
                                    .font(.body)
                                    .foregroundStyle(.primary)
                                    .multilineTextAlignment(.leading)
                            }
                        }
                        .swipeActions {
                            Button(role: .destructive) {
                                Task { await vm.delete(template) }
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
        .sheet(item: $vm.editingTemplate) { template in
            NavigationStack {
                Form {
                    Section("Time") {
                        Picker("Hour", selection: $vm.editHour) {
                            ForEach(0..<24, id: \.self) { hour in
                                Text(DayLogViewModel.hourLabel(hour)).tag(hour)
                            }
                        }
                    }
                    Section("What you usually eat") {
                        TextField("Food or meal…", text: $vm.editNutrition, axis: .vertical)
                            .lineLimit(2...6)
                    }
                    Section {
                        Toggle("Active", isOn: $vm.editIsActive)
                    }
                    if case .error(let message) = vm.editStatus {
                        Section {
                            Text(message).font(.footnote).foregroundStyle(.red)
                        }
                    }
                }
                .navigationTitle("Edit template")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .cancellationAction) {
                        Button("Cancel") { vm.editingTemplate = nil }
                    }
                    ToolbarItem(placement: .confirmationAction) {
                        Button("Save") {
                            Task { await vm.saveEdit() }
                        }
                        .disabled(vm.editStatus == .saving)
                    }
                }
            }
            .presentationDetents([.medium, .large])
        }
    }
}
