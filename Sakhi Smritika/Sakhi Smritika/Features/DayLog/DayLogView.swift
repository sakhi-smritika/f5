import SwiftUI

struct DayLogView: View {
    @Environment(AuthService.self) private var authService
    @Environment(AppDependencies.self) private var dependencies
    @State private var viewModel: DayLogViewModel?

    var body: some View {
        NavigationStack {
            Group {
                if let viewModel {
                    dayLogContent(viewModel)
                } else {
                    LoadingView()
                }
            }
            .navigationTitle("Day Log")
        }
        .task {
            if viewModel == nil {
                viewModel = DayLogViewModel(
                    authService: authService,
                    cache: dependencies.cache,
                    refreshTracker: dependencies.refreshTracker
                )
            }
            await viewModel?.appear()
        }
    }

    @ViewBuilder
    private func dayLogContent(_ vm: DayLogViewModel) -> some View {
        @Bindable var vm = vm

        ScrollView {
            VStack(alignment: .leading, spacing: 20) {
                DateNavigator(dateISO: $vm.dateISO)
                    .padding(.horizontal, 4)
                    .onChange(of: vm.dateISO) { _, _ in
                        Task { await vm.dateChanged() }
                    }

                if vm.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                } else if let loadError = vm.loadError {
                    Text(loadError)
                        .font(.footnote)
                        .foregroundStyle(.red)
                } else {
                    CollapsibleSection(title: "Hours", isOpen: $vm.isHoursOpen) {
                        hoursContent(vm)
                    }

                    CollapsibleSection(title: "Nutrition", isOpen: $vm.isNutritionOpen) {
                        nutritionContent(vm)
                    }

                    if case .error(let message) = vm.saveStatus {
                        Text(message)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }

                    SaveButton(status: vm.saveStatus) {
                        Task { await vm.save() }
                    }
                }
            }
            .padding(20)
        }
        .scrollDismissesKeyboard(.interactively)
        .background(Color(.systemGroupedBackground))
        .onAppear { vm.reloadHourGroups() }
        .sheet(isPresented: $vm.isAddingNutritionEntry) {
            NutritionEntryEditorSheet(
                title: "Add entry",
                hour: $vm.draftHour,
                food: $vm.draftFood,
                onSave: { vm.commitDraftNutritionEntry() },
                onCancel: { vm.cancelDraftNutritionEntry() }
            )
        }
        .sheet(item: $vm.editingNutritionEntry) { _ in
            NutritionEntryEditorSheet(
                title: "Edit entry",
                hour: $vm.draftHour,
                food: $vm.draftFood,
                onSave: { vm.commitDraftNutritionEntry() },
                onCancel: { vm.cancelDraftNutritionEntry() }
            )
        }
    }

    @ViewBuilder
    private func hoursContent(_ vm: DayLogViewModel) -> some View {
        VStack(alignment: .leading, spacing: 20) {
            ForEach(DayLogPeriod.allCases) { period in
                let hours = vm.hourGroups.hours(for: period)
                if !hours.isEmpty {
                    VStack(alignment: .leading, spacing: 12) {
                        Text(period.title)
                            .font(.caption.weight(.bold))
                            .foregroundStyle(.secondary)
                            .textCase(.uppercase)

                        ForEach(hours, id: \.self) { hour in
                            hourRow(vm, hour: hour)
                        }
                    }
                }
            }
        }
    }

    private func hourRow(_ vm: DayLogViewModel, hour: Int) -> some View {
        VStack(alignment: .leading, spacing: 6) {
            Text(DayLogViewModel.hourLabel(hour))
                .font(.caption.weight(.semibold))
                .foregroundStyle(.secondary)

            TextField(
                "Notes…",
                text: Binding(
                    get: { vm.dayLog[String(hour)] ?? "" },
                    set: { vm.setHour(hour, value: $0) }
                ),
                axis: .vertical
            )
            .lineLimit(1...4)
            .padding(14)
            .background(
                Color(.tertiarySystemFill),
                in: RoundedRectangle(cornerRadius: 14, style: .continuous)
            )
            .overlay(
                RoundedRectangle(cornerRadius: 14, style: .continuous)
                    .strokeBorder(Color.primary.opacity(0.08), lineWidth: 1)
            )
        }
    }

    @ViewBuilder
    private func nutritionContent(_ vm: DayLogViewModel) -> some View {
        let swipables = vm.swipableTemplates()

        VStack(alignment: .leading, spacing: 20) {
            if !swipables.isEmpty {
                VStack(alignment: .leading, spacing: 12) {
                    subsectionLabel("Templates")

                    ForEach(swipables) { template in
                        templateRow(vm, template: template)
                    }
                }
            }

            if let templateSaveError = vm.templateSaveError {
                Text(templateSaveError)
                    .font(.footnote)
                    .foregroundStyle(.red)
            }

            VStack(alignment: .leading, spacing: 12) {
                HStack {
                    subsectionLabel("Entries")
                    Spacer()
                    Button {
                        vm.beginAddNutritionEntry()
                    } label: {
                        Label("Add", systemImage: "plus")
                            .font(.caption.weight(.semibold))
                    }
                }

                if vm.sortedNutritionEntries.isEmpty {
                    Text("No nutrition logged yet.")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                } else {
                    ForEach(vm.sortedNutritionEntries) { entry in
                        nutritionEntryRow(vm, entry: entry)
                    }
                }
            }
        }
    }

    private func subsectionLabel(_ title: String) -> some View {
        Text(title)
            .font(.caption.weight(.bold))
            .foregroundStyle(.secondary)
            .textCase(.uppercase)
    }

    private func templateRow(_ vm: DayLogViewModel, template: NutritionTemplate) -> some View {
        SwipeActionRow(
            leading: SwipeActionRow.Action(
                title: "Log",
                systemImage: "plus",
                tint: .green
            ) {
                Task { await vm.addFromTemplate(template) }
            }
        ) {
            VStack(alignment: .leading, spacing: 6) {
                Text(DayLogViewModel.hourLabel(template.hour))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                Text(template.nutrition)
                    .font(.subheadline)
                    .foregroundStyle(.primary)
            }
            .padding(14)
        }
    }

    private func nutritionEntryRow(_ vm: DayLogViewModel, entry: EditableNutritionEntry) -> some View {
        SwipeActionRow(
            trailing: SwipeActionRow.Action(
                title: "Delete",
                systemImage: "trash",
                tint: .red
            ) {
                vm.deleteNutritionEntry(entry)
            },
            onTap: {
                vm.beginEditNutritionEntry(entry)
            }
        ) {
            HStack(alignment: .top, spacing: 12) {
                Text(DayLogViewModel.hourLabel(entry.hour))
                    .font(.caption.weight(.semibold))
                    .foregroundStyle(.secondary)
                    .frame(width: 96, alignment: .leading)
                Text(entry.food)
                    .font(.subheadline)
                    .foregroundStyle(.primary)
                    .multilineTextAlignment(.leading)
                Spacer(minLength: 0)
            }
            .padding(14)
        }
    }
}
