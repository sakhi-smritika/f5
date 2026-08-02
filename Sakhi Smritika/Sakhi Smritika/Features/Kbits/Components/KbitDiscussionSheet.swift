import SwiftUI

struct KbitDiscussionSheet: View {
    let bit: KnowledgeBit
    /// Owned by `ChatThreadRegistry`, so reopening the sheet keeps the transcript,
    /// the draft, and any running stream.
    let viewModel: ChatThreadViewModel

    @Environment(\.dismiss) private var dismiss
    @FocusState private var focused: Bool

    var body: some View {
        NavigationStack {
            discussionContent(viewModel)
                .navigationTitle("Discussion")
                .navigationBarTitleDisplayMode(.inline)
                .toolbar {
                    ToolbarItem(placement: .topBarTrailing) {
                        Button("Done") { dismiss() }
                    }
                }
                .task { await viewModel.appear() }
        }
        .presentationDetents([.medium, .large])
        .presentationDragIndicator(.visible)
    }

    @ViewBuilder
    private func discussionContent(_ vm: ChatThreadViewModel) -> some View {
        @Bindable var vm = vm

        VStack(spacing: 0) {
            VStack(alignment: .leading, spacing: 6) {
                Text(bit.title)
                    .font(.subheadline.weight(.semibold))
                    .lineLimit(2)
                Text(bit.content)
                    .font(.caption)
                    .foregroundStyle(.secondary)
                    .lineLimit(3)
            }
            .frame(maxWidth: .infinity, alignment: .leading)
            .padding(.horizontal, 16)
            .padding(.vertical, 10)

            Divider()

            ScrollViewReader { proxy in
                ScrollView {
                    LazyVStack(alignment: .leading, spacing: 12) {
                        if vm.isLoading {
                            ProgressView()
                                .frame(maxWidth: .infinity)
                                .padding(.vertical, 32)
                        } else if let loadError = vm.loadError, vm.messages.isEmpty {
                            Text(loadError)
                                .font(.footnote)
                                .foregroundStyle(.red)
                                .padding()
                        } else if vm.messages.isEmpty {
                            ContentUnavailableView(
                                "Start the discussion",
                                systemImage: "bubble.left.and.bubble.right",
                                description: Text("Add a comment to talk about this with Sakhi.")
                            )
                            .padding(.top, 24)
                        } else {
                            ForEach(vm.messages) { message in
                                MessageBubbleView(
                                    message: message,
                                    isStreaming: vm.isStreaming
                                        && message.id == vm.messages.last?.id
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
                .onChange(of: vm.messages) { _, value in
                    if let last = value.last?.id {
                        withAnimation(.easeOut(duration: 0.2)) {
                            proxy.scrollTo(last, anchor: .bottom)
                        }
                    }
                }
            }

            if let sendError = vm.sendError {
                Text(sendError)
                    .font(.caption)
                    .foregroundStyle(.red)
                    .padding(.horizontal, 16)
            }

            HStack(alignment: .bottom, spacing: 10) {
                TextField("Add a comment…", text: $vm.draft, axis: .vertical)
                    .lineLimit(1...5)
                    .focused($focused)
                    .padding(12)
                    .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 16, style: .continuous))

                Button {
                    Task { await vm.send() }
                } label: {
                    Image(systemName: "arrow.up.circle.fill")
                        .font(.system(size: 30))
                }
                .disabled(!vm.canSend)
            }
            .padding(12)
            .background(.ultraThinMaterial)
        }
    }
}
