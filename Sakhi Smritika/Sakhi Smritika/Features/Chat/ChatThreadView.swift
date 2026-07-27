import PhotosUI
import SwiftUI
import UniformTypeIdentifiers

struct ChatThreadView: View {
    /// Owned by `ChatThreadRegistry`, not by this view, so a draft in the
    /// composer and any running stream survive navigating away and back.
    let viewModel: ChatThreadViewModel
    let listViewModel: ChatListViewModel

    @State private var photoItems: [PhotosPickerItem] = []
    @State private var showFileImporter = false
    @FocusState private var composerFocused: Bool

    var body: some View {
        threadContent(viewModel)
            .navigationTitle(viewModel.title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                if viewModel.models.count > 1 {
                    ToolbarItem(placement: .topBarTrailing) {
                        Menu {
                            Picker("Model", selection: Binding(
                                get: { viewModel.selectedModelId },
                                set: { id in
                                    viewModel.selectedModelId = id
                                    listViewModel.selectModel(id)
                                }
                            )) {
                                ForEach(viewModel.models) { model in
                                    Text(model.label).tag(model.id)
                                }
                            }
                        } label: {
                            Image(systemName: "cpu")
                        }
                        .accessibilityLabel("Model: \(viewModel.selectedModelLabel)")
                    }
                }
            }
            .toolbar {
                ToolbarItemGroup(placement: .keyboard) {
                    Spacer()
                    Button("Done") {
                        composerFocused = false
                    }
                }
            }
            .task {
                viewModel.syncModels(
                    listViewModel.models,
                    selectedModelId: listViewModel.selectedModelId
                )
                await viewModel.appear()
            }
    }

    @ViewBuilder
    private func threadContent(_ vm: ChatThreadViewModel) -> some View {
        @Bindable var vm = vm

        VStack(spacing: 0) {
            messageScroll(vm)

            if let sendError = vm.sendError {
                Text(sendError)
                    .font(.footnote)
                    .foregroundStyle(.red)
                    .frame(maxWidth: .infinity, alignment: .leading)
                    .padding(.horizontal, 16)
                    .padding(.top, 8)
            }

            composer(vm)
        }
        .background(Color(.systemGroupedBackground))
        .onChange(of: photoItems) { _, items in
            guard !items.isEmpty else { return }
            Task {
                var files: [(Data, String, String)] = []
                for item in items {
                    if let data = try? await item.loadTransferable(type: Data.self) {
                        let filename = "photo-\(UUID().uuidString.prefix(8)).jpg"
                        files.append((data, filename, "image/jpeg"))
                    }
                }
                photoItems = []
                await vm.addFiles(files)
            }
        }
        .fileImporter(
            isPresented: $showFileImporter,
            allowedContentTypes: [.item],
            allowsMultipleSelection: true
        ) { result in
            guard case .success(let urls) = result else { return }
            Task {
                var files: [(Data, String, String)] = []
                for url in urls {
                    let accessed = url.startAccessingSecurityScopedResource()
                    defer { if accessed { url.stopAccessingSecurityScopedResource() } }
                    if let data = try? Data(contentsOf: url) {
                        let mime = UTType(filenameExtension: url.pathExtension)?.preferredMIMEType
                            ?? "application/octet-stream"
                        files.append((data, url.lastPathComponent, mime))
                    }
                }
                await vm.addFiles(files)
            }
        }
    }

    private func messageScroll(_ vm: ChatThreadViewModel) -> some View {
        ScrollViewReader { proxy in
            ScrollView {
                LazyVStack(alignment: .leading, spacing: 14) {
                    if let pinned = vm.pinnedKbit {
                        PinnedKbitCard(bit: pinned)
                    }

                    if vm.isLoading {
                        ProgressView()
                            .frame(maxWidth: .infinity)
                            .padding(.vertical, 40)
                    } else if let loadError = vm.loadError {
                        Text(loadError)
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .padding()
                    } else if vm.messages.isEmpty {
                        ContentUnavailableView(
                            vm.isKbitDiscussion
                                ? "Start the discussion"
                                : "Ask Sakhi anything",
                            systemImage: "sparkles",
                            description: Text(
                                vm.isKbitDiscussion
                                    ? "Add a comment to discuss this with Smritika."
                                    : "Send a message to get started."
                            )
                        )
                        .padding(.top, vm.pinnedKbit == nil ? 48 : 12)
                    } else {
                        ForEach(vm.messages) { message in
                            MessageBubbleView(
                                message: message,
                                isStreaming: vm.isStreaming && message.id == vm.messages.last?.id
                                    && message.role == .assistant
                            )
                            .id(message.id)
                        }
                    }
                }
                .padding(16)
            }
            .scrollDismissesKeyboard(.interactively)
            .refreshable { await vm.reload() }
            .onTapGesture {
                composerFocused = false
            }
            .onChange(of: vm.messages) { _, messages in
                if let last = messages.last?.id {
                    withAnimation(.easeOut(duration: 0.2)) {
                        proxy.scrollTo(last, anchor: .bottom)
                    }
                }
            }
        }
    }

    private func composer(_ vm: ChatThreadViewModel) -> some View {
        @Bindable var vm = vm

        return VStack(alignment: .leading, spacing: 10) {
            if let quote = vm.quote {
                HStack {
                    Text(quote)
                        .font(.caption)
                        .lineLimit(2)
                        .foregroundStyle(.secondary)
                    Spacer()
                    Button {
                        vm.quote = nil
                    } label: {
                        Image(systemName: "xmark.circle.fill")
                            .foregroundStyle(.tertiary)
                    }
                }
                .padding(10)
                .background(.quaternary.opacity(0.5), in: RoundedRectangle(cornerRadius: 10, style: .continuous))
            }

            if !vm.pendingAttachments.isEmpty {
                ScrollView(.horizontal, showsIndicators: false) {
                    HStack(spacing: 8) {
                        ForEach(vm.pendingAttachments) { attachment in
                            HStack(spacing: 6) {
                                if attachment.isUploading {
                                    ProgressView().controlSize(.mini)
                                }
                                Text(attachment.filename)
                                    .font(.caption)
                                    .lineLimit(1)
                                Button {
                                    Task { await vm.removePendingAttachment(attachment) }
                                } label: {
                                    Image(systemName: "xmark.circle.fill")
                                        .font(.caption)
                                }
                            }
                            .padding(.horizontal, 10)
                            .padding(.vertical, 6)
                            .background(.regularMaterial, in: Capsule())
                        }
                    }
                }
            }

            HStack(alignment: .bottom, spacing: 10) {
                Menu {
                    PhotosPicker(selection: $photoItems, maxSelectionCount: 4, matching: .images) {
                        Label("Photos", systemImage: "photo")
                    }
                    Button {
                        showFileImporter = true
                    } label: {
                        Label("Files", systemImage: "doc")
                    }
                } label: {
                    Image(systemName: "paperclip")
                        .font(.title3)
                        .frame(width: 36, height: 36)
                }
                .disabled(vm.isStreaming)

                TextField("Message", text: $vm.draft, axis: .vertical)
                    .lineLimit(1...6)
                    .focused($composerFocused)
                    .padding(12)
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 18, style: .continuous))

                if composerFocused {
                    Button {
                        composerFocused = false
                    } label: {
                        Image(systemName: "keyboard.chevron.compact.down")
                            .font(.title3)
                            .frame(width: 36, height: 36)
                    }
                    .accessibilityLabel("Hide keyboard")
                }

                Button {
                    composerFocused = false
                    Task { await vm.send() }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 32))
                        .symbolRenderingMode(.hierarchical)
                }
                .disabled(!vm.canSend)
            }
        }
        .padding(.horizontal, 16)
        .padding(.vertical, 12)
        .background(.ultraThinMaterial)
    }
}

struct PinnedKbitCard: View {
    let bit: KnowledgeBit

    var body: some View {
        VStack(alignment: .leading, spacing: 8) {
            Text("Knowledge Bit")
                .font(.caption.weight(.semibold))
                .foregroundStyle(Color.accentColor)
                .textCase(.uppercase)

            Text(bit.title)
                .font(.headline)

            Text(bit.content)
                .font(.subheadline)
                .foregroundStyle(.secondary)
                .fixedSize(horizontal: false, vertical: true)
        }
        .frame(maxWidth: .infinity, alignment: .leading)
        .padding(14)
        .background(Color.accentColor.opacity(0.08), in: RoundedRectangle(cornerRadius: 14, style: .continuous))
        .overlay(
            RoundedRectangle(cornerRadius: 14, style: .continuous)
                .strokeBorder(Color.accentColor.opacity(0.35), lineWidth: 1)
        )
        .accessibilityElement(children: .combine)
        .accessibilityLabel("Knowledge Bit: \(bit.title)")
    }
}

struct MessageBubbleView: View {
    let message: ChatMessage
    var isStreaming: Bool = false

    private var isUser: Bool { message.role == .user }

    var body: some View {
        HStack {
            if isUser { Spacer(minLength: 48) }

            VStack(alignment: isUser ? .trailing : .leading, spacing: 6) {
                if let attachments = message.attachments, !attachments.isEmpty {
                    ForEach(attachments) { attachment in
                        Label(attachment.filename, systemImage: "paperclip")
                            .font(.caption)
                            .foregroundStyle(.secondary)
                    }
                }

                if isUser {
                    Text(message.text)
                        .textSelection(.enabled)
                        .padding(12)
                        .background(
                            Color.accentColor.opacity(0.18),
                            in: RoundedRectangle(cornerRadius: 16, style: .continuous)
                        )
                } else {
                    if let toolSteps = message.toolSteps, !toolSteps.isEmpty {
                        ToolStepsView(steps: toolSteps)
                    }
                    if !message.text.isEmpty || isStreaming {
                        ChatMarkdownView(text: message.text, isStreaming: isStreaming)
                    }
                }
            }

            if !isUser { Spacer(minLength: 0) }
        }
    }
}
