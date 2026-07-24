import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

struct ChatListView: View {
    @Environment(AuthService.self) private var authService
    @Environment(AppDependencies.self) private var dependencies
    @State private var viewModel: ChatListViewModel?
    @State private var path = NavigationPath()
    @State private var draftToken = UUID()

    private enum Route: Hashable {
        case draft(UUID)
        case conversation(UUID)
    }

    var body: some View {
        NavigationStack(path: $path) {
            Group {
                if let viewModel {
                    listContent(viewModel)
                } else {
                    LoadingView(message: "Loading chats…")
                }
            }
            .navigationTitle("Chat")
            .toolbar {
                ToolbarItem(placement: .topBarTrailing) {
                    Button {
                        draftToken = UUID()
                        path.append(Route.draft(draftToken))
                    } label: {
                        Image(systemName: "square.and.pencil")
                    }
                    .accessibilityLabel("New conversation")
                }
            }
            .navigationDestination(for: Route.self) { route in
                if let viewModel {
                    switch route {
                    case .draft:
                        ChatThreadView(
                            conversation: nil,
                            listViewModel: viewModel
                        )
                    case .conversation(let id):
                        ChatThreadView(
                            conversation: viewModel.conversations.first(where: { $0.id == id }),
                            listViewModel: viewModel
                        )
                    }
                }
            }
            .task {
                if viewModel == nil {
                    viewModel = ChatListViewModel(
                        authService: authService,
                        apiClient: dependencies.apiClient
                    )
                }
                await viewModel?.load()
            }
        }
    }

    @ViewBuilder
    private func listContent(_ vm: ChatListViewModel) -> some View {
        @Bindable var vm = vm

        List {
            if let loadError = vm.loadError {
                Section {
                    Text(loadError).foregroundStyle(.red).font(.footnote)
                }
            }

            Section {
                Button {
                    draftToken = UUID()
                    path.append(Route.draft(draftToken))
                } label: {
                    Label("New chat", systemImage: "plus.message")
                }
            }

            Section {
                Button {
                    vm.newFolderName = ""
                    vm.showNewFolderAlert = true
                } label: {
                    Label("New folder", systemImage: "folder.badge.plus")
                }

                ForEach(vm.folders) { folder in
                    DisclosureGroup(
                        isExpanded: Binding(
                            get: { vm.expandedFolderIds.contains(folder.id) },
                            set: { expanded in
                                if expanded {
                                    vm.expandedFolderIds.insert(folder.id)
                                } else {
                                    vm.expandedFolderIds.remove(folder.id)
                                }
                            }
                        )
                    ) {
                        ForEach(vm.conversations(in: folder.id)) { conversation in
                            conversationRow(conversation, vm: vm)
                        }
                    } label: {
                        Label(folder.name, systemImage: "folder")
                    }
                    .contextMenu {
                        Button("Delete", role: .destructive) {
                            vm.folderToDelete = folder
                        }
                    }
                }
            } header: {
                Text("Folders")
            }

            Section {
                if vm.isLoading {
                    ProgressView()
                } else if vm.unfolderedConversations.isEmpty && vm.folders.isEmpty {
                    ContentUnavailableView(
                        "No conversations yet",
                        systemImage: "bubble.left.and.bubble.right",
                        description: Text("Start a new chat to talk with Sakhi.")
                    )
                } else {
                    ForEach(vm.unfolderedConversations) { conversation in
                        conversationRow(conversation, vm: vm)
                    }
                }
            } header: {
                Text("Chats")
            }
        }
        .listStyle(.insetGrouped)
        .refreshable { await vm.load() }
        .alert("New folder", isPresented: $vm.showNewFolderAlert) {
            TextField("Name", text: $vm.newFolderName)
            Button("Create") {
                Task { await vm.createFolder() }
            }
            Button("Cancel", role: .cancel) {}
        }
        .confirmationDialog(
            "Delete folder and all chats inside?",
            isPresented: Binding(
                get: { vm.folderToDelete != nil },
                set: { if !$0 { vm.folderToDelete = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                if let folder = vm.folderToDelete {
                    Task { await vm.deleteFolder(folder) }
                }
            }
            Button("Cancel", role: .cancel) {
                vm.folderToDelete = nil
            }
        }
        .confirmationDialog(
            "Delete this conversation?",
            isPresented: Binding(
                get: { vm.conversationToDelete != nil },
                set: { if !$0 { vm.conversationToDelete = nil } }
            ),
            titleVisibility: .visible
        ) {
            Button("Delete", role: .destructive) {
                if let conversation = vm.conversationToDelete {
                    Task { await vm.deleteConversation(conversation) }
                }
            }
            Button("Cancel", role: .cancel) {
                vm.conversationToDelete = nil
            }
        }
    }

    private func conversationRow(_ conversation: Conversation, vm: ChatListViewModel) -> some View {
        NavigationLink(value: Route.conversation(conversation.id)) {
            HStack(spacing: 10) {
                if conversation.kbitId != nil {
                    Image(systemName: "sparkles")
                        .font(.footnote)
                        .foregroundStyle(.secondary)
                        .accessibilityLabel("Knowledge bit discussion")
                }
                VStack(alignment: .leading, spacing: 4) {
                    Text(conversation.displayTitle)
                        .font(.body.weight(.medium))
                        .lineLimit(1)
                    if let updated = conversation.updatedAt {
                        Text(updated)
                            .font(.caption2)
                            .foregroundStyle(.tertiary)
                            .lineLimit(1)
                    }
                }
            }
        }
        .contextMenu {
            Menu("Move to folder") {
                Button("Remove from folder") {
                    Task { await vm.moveConversation(conversation, to: nil) }
                }
                ForEach(vm.folders) { folder in
                    Button(folder.name) {
                        Task { await vm.moveConversation(conversation, to: folder.id) }
                    }
                }
            }
            Button("Delete", role: .destructive) {
                vm.conversationToDelete = conversation
            }
        }
    }
}
