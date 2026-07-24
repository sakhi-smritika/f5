import SwiftUI

enum AppTab: Hashable {
    case diary
    case dayLog
    case chat
    case kbits
    case more
}

struct MainTabView: View {
    @Environment(AuthService.self) private var authService
    @State private var selectedTab: AppTab = .chat
    /// Tab to restore when leaving a More destination screen.
    @State private var previousTab: AppTab = .chat
    @State private var moreMenuOpen = false
    @State private var moreDestination: MoreDestination?
    @State private var showSignOutConfirm = false

    private var tabSelection: Binding<AppTab> {
        Binding(
            get: { selectedTab },
            set: { newValue in
                if newValue == .more {
                    // More tab button only toggles the vertical icon bar.
                    withAnimation(.smooth(duration: 0.22)) {
                        moreMenuOpen.toggle()
                    }
                } else {
                    selectedTab = newValue
                    previousTab = newValue
                    moreDestination = nil
                    if moreMenuOpen {
                        withAnimation(.smooth(duration: 0.18)) {
                            moreMenuOpen = false
                        }
                    }
                }
            }
        )
    }

    var body: some View {
        TabView(selection: tabSelection) {
            Tab("Diary", systemImage: "book.closed", value: .diary) {
                DiaryView()
            }

            Tab("Day Log", systemImage: "clock", value: .dayLog) {
                DayLogView()
            }

            Tab("Chat", systemImage: "bubble.left.and.bubble.right", value: .chat) {
                ChatListView()
            }

            Tab("Kbits", systemImage: "sparkles", value: .kbits) {
                KbitsFeedView()
            }

            Tab("More", systemImage: "ellipsis", value: .more) {
                moreTabRoot
            }
        }
        .sensoryFeedback(.selection, trigger: selectedTab)
        .overlay {
            if moreMenuOpen {
                Color.black.opacity(0.001)
                    .ignoresSafeArea()
                    .onTapGesture {
                        withAnimation(.smooth(duration: 0.18)) {
                            moreMenuOpen = false
                        }
                    }
            }
        }
        .overlay(alignment: .bottomTrailing) {
            if moreMenuOpen {
                MoreMenuView(
                    onSelect: openMoreDestination,
                    onSignOut: {
                        withAnimation(.smooth(duration: 0.18)) {
                            moreMenuOpen = false
                        }
                        showSignOutConfirm = true
                    }
                )
                .fixedSize()
                .padding(.trailing, 22)
                .padding(.bottom, 52)
                .transition(.opacity.combined(with: .scale(scale: 0.95, anchor: .bottomTrailing)))
            }
        }
        .confirmationDialog(
            "Sign out of Sakhi Smritika?",
            isPresented: $showSignOutConfirm,
            titleVisibility: .visible
        ) {
            Button("Log Out", role: .destructive) {
                Task { await authService.signOut() }
            }
            Button("Cancel", role: .cancel) {}
        }
    }

    @ViewBuilder
    private var moreTabRoot: some View {
        NavigationStack {
            Group {
                switch moreDestination {
                case .profile:
                    ProfileView()
                case .goals:
                    GoalsListView()
                case .settings:
                    SettingsView()
                case nil:
                    Color.clear
                        .accessibilityHidden(true)
                }
            }
            .toolbar {
                if moreDestination != nil {
                    ToolbarItem(placement: .topBarLeading) {
                        Button {
                            closeMoreDestination()
                        } label: {
                            HStack(spacing: 4) {
                                Image(systemName: "chevron.left")
                                Text("Back")
                            }
                        }
                    }
                }
            }
        }
    }

    private func openMoreDestination(_ destination: MoreDestination) {
        withAnimation(.smooth(duration: 0.18)) {
            moreMenuOpen = false
        }
        if selectedTab != .more {
            previousTab = selectedTab
        }
        moreDestination = destination
        selectedTab = .more
    }

    private func closeMoreDestination() {
        moreDestination = nil
        selectedTab = previousTab
    }
}
