import SwiftUI

struct SettingsView: View {
    @Environment(AppDependencies.self) private var dependencies
    @State private var viewModel: SettingsViewModel?

    var body: some View {
        Group {
            if let viewModel {
                settingsContent(viewModel)
            } else {
                LoadingView()
            }
        }
        .navigationTitle("Settings")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if viewModel == nil {
                viewModel = SettingsViewModel(
                    apiClient: dependencies.apiClient,
                    cache: dependencies.cache,
                    refreshTracker: dependencies.refreshTracker
                )
            }
            await viewModel?.appear()
        }
    }

    @ViewBuilder
    private func settingsContent(_ vm: SettingsViewModel) -> some View {
        @Bindable var vm = vm

        List {
            if let flash = vm.flashMessage {
                Section {
                    Text(flash)
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
            }

            if let loadError = vm.loadError {
                Section {
                    Text(loadError)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
            }

            if let actionError = vm.actionError {
                Section {
                    Text(actionError)
                        .font(.footnote)
                        .foregroundStyle(.red)
                }
            }

            Section {
                HStack {
                    VStack(alignment: .leading, spacing: 4) {
                        Text("Google")
                            .font(.body.weight(.medium))
                        if vm.isConnected, let email = vm.status?.googleEmail, !email.isEmpty {
                            Text(email)
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        } else {
                            Text("Calendar & Tasks for chat")
                                .font(.footnote)
                                .foregroundStyle(.secondary)
                        }
                    }

                    Spacer()

                    if vm.isLoading || vm.isBusy {
                        ProgressView()
                            .controlSize(.small)
                    } else {
                        Toggle(
                            "Google",
                            isOn: Binding(
                                get: { vm.isConnected },
                                set: { _ in
                                    Task { await vm.toggleGoogle() }
                                }
                            )
                        )
                        .labelsHidden()
                        .disabled(vm.loadError != nil)
                    }
                }
                .padding(.vertical, 4)
            } footer: {
                Text("Connect your Google account so Sakhi can manage Calendar and Tasks on your behalf.")
            }
        }
        .listStyle(.insetGrouped)
        .scrollContentBackground(.hidden)
        .background(Color(.systemGroupedBackground))
        .refreshable {
            await vm.reload()
        }
    }
}
