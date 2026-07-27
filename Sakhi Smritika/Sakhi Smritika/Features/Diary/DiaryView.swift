import SwiftUI

struct DiaryView: View {
    @Environment(AuthService.self) private var authService
    @Environment(AppDependencies.self) private var dependencies
    @State private var viewModel: DiaryViewModel?

    var body: some View {
        NavigationStack {
            Group {
                if let viewModel {
                    diaryContent(viewModel)
                } else {
                    LoadingView()
                }
            }
            .navigationTitle("Diary")
        }
        .task {
            if viewModel == nil {
                viewModel = DiaryViewModel(
                    authService: authService,
                    cache: dependencies.cache,
                    refreshTracker: dependencies.refreshTracker
                )
            }
            await viewModel?.appear()
        }
    }

    @ViewBuilder
    private func diaryContent(_ vm: DiaryViewModel) -> some View {
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
                    collapsibleSection(
                        title: "How was the day?",
                        isOpen: $vm.isHowOpen,
                        text: $vm.howWasTheDay,
                        placeholder: "A short reflection…"
                    ) { vm.markEdited() }

                    collapsibleSection(
                        title: "Major events",
                        isOpen: $vm.isMajorOpen,
                        text: $vm.majorEvents,
                        placeholder: "What stood out?"
                    ) { vm.markEdited() }

                    collapsibleSection(
                        title: "General",
                        isOpen: $vm.isGeneralOpen,
                        text: $vm.generalContent,
                        placeholder: "Anything else…"
                    ) { vm.markEdited() }

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
    }

    private func collapsibleSection(
        title: String,
        isOpen: Binding<Bool>,
        text: Binding<String>,
        placeholder: String,
        onEdit: @escaping () -> Void
    ) -> some View {
        VStack(alignment: .leading, spacing: 10) {
            Button {
                withAnimation(.snappy) { isOpen.wrappedValue.toggle() }
            } label: {
                HStack {
                    Text(title)
                        .font(.subheadline.weight(.semibold))
                        .foregroundStyle(.primary)
                    Spacer()
                    Image(systemName: "chevron.down")
                        .font(.caption.weight(.semibold))
                        .foregroundStyle(.secondary)
                        .rotationEffect(.degrees(isOpen.wrappedValue ? 0 : -90))
                }
            }
            .buttonStyle(.plain)

            if isOpen.wrappedValue {
                TextField(placeholder, text: text, axis: .vertical)
                    .lineLimit(4...12)
                    .padding(14)
                    .background(
                        Color(.tertiarySystemFill),
                        in: RoundedRectangle(cornerRadius: 14, style: .continuous)
                    )
                    .overlay(
                        RoundedRectangle(cornerRadius: 14, style: .continuous)
                            .strokeBorder(Color.primary.opacity(0.08), lineWidth: 1)
                    )
                    .onChange(of: text.wrappedValue) { _, _ in onEdit() }
            }
        }
        .padding(16)
        .background(
            Color(.secondarySystemGroupedBackground),
            in: RoundedRectangle(cornerRadius: 18, style: .continuous)
        )
        .overlay(
            RoundedRectangle(cornerRadius: 18, style: .continuous)
                .strokeBorder(Color.primary.opacity(0.12), lineWidth: 1)
        )
    }
}
