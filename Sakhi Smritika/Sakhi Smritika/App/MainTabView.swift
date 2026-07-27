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
    @State private var showSignOutConfirm = false

    var body: some View {
        TabView(selection: $selectedTab) {
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
                MoreView(onSignOut: { showSignOutConfirm = true })
            }
        }
        .sensoryFeedback(.selection, trigger: selectedTab)
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
}
