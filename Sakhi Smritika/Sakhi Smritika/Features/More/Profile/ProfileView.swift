import SwiftUI

struct ProfileView: View {
    @Environment(AuthService.self) private var authService
    @State private var viewModel: ProfileViewModel?

    var body: some View {
        Group {
            if let viewModel {
                profileContent(viewModel)
            } else {
                LoadingView()
            }
        }
        .navigationTitle("Profile")
        .navigationBarTitleDisplayMode(.inline)
        .task {
            if viewModel == nil {
                viewModel = ProfileViewModel(authService: authService)
            }
            await viewModel?.load()
        }
    }

    @ViewBuilder
    private func profileContent(_ vm: ProfileViewModel) -> some View {
        @Bindable var vm = vm

        ScrollView {
            VStack(alignment: .leading, spacing: 18) {
                if vm.isLoading {
                    ProgressView()
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 40)
                } else if let loadError = vm.loadError {
                    Text(loadError)
                        .font(.footnote)
                        .foregroundStyle(.red)
                } else {
                    field(title: "Full name") {
                        TextField("Your full name", text: $vm.fullName)
                            .textContentType(.name)
                            .padding(14)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .onChange(of: vm.fullName) { _, _ in vm.markEdited() }
                    }

                    field(title: "About you") {
                        TextField("What should Sakhi know about you?", text: $vm.userInformation, axis: .vertical)
                            .lineLimit(4...10)
                            .padding(14)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .onChange(of: vm.userInformation) { _, _ in vm.markEdited() }
                    }

                    field(title: "System instructions") {
                        TextField("How should Sakhi behave?", text: $vm.systemInstructions, axis: .vertical)
                            .lineLimit(4...10)
                            .padding(14)
                            .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))
                            .onChange(of: vm.systemInstructions) { _, _ in vm.markEdited() }
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
    }

    private func field<Content: View>(title: String, @ViewBuilder content: () -> Content) -> some View {
        VStack(alignment: .leading, spacing: 8) {
            Text(title)
                .font(.subheadline.weight(.semibold))
                .foregroundStyle(.secondary)
            content()
        }
    }
}
