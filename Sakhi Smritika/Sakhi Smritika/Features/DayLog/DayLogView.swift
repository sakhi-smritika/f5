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
            VStack(alignment: .leading, spacing: 16) {
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
                    ForEach(DayLogViewModel.hours, id: \.self) { hour in
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
                            .padding(12)
                            .background(
                                Color(.secondarySystemGroupedBackground),
                                in: RoundedRectangle(cornerRadius: 12, style: .continuous)
                            )
                            .overlay(
                                RoundedRectangle(cornerRadius: 12, style: .continuous)
                                    .strokeBorder(Color.primary.opacity(0.12), lineWidth: 1)
                            )
                        }
                    }

                    if case .error(let message) = vm.saveStatus {
                        Text(message)
                            .font(.footnote)
                            .foregroundStyle(.red)
                    }

                    SaveButton(status: vm.saveStatus) {
                        Task { await vm.save() }
                    }
                    .padding(.top, 8)
                }
            }
            .padding(20)
        }
        .scrollDismissesKeyboard(.interactively)
        .background(Color(.systemGroupedBackground))
    }
}
