import SwiftUI

struct RootView: View {
    @Environment(AuthService.self) private var authService
    @Environment(AppDependencies.self) private var dependencies

    /// View models hydrate from the cache in their initialisers, so the tabs must
    /// not be built until the cache is confirmed to belong to this account.
    @State private var preparedUserId: UUID?

    var body: some View {
        Group {
            if authService.isLoading {
                LoadingView(message: "Preparing Sakhi…")
            } else if authService.isAuthenticated {
                if let userId = authService.userId, preparedUserId == userId {
                    MainTabView()
                } else {
                    LoadingView(message: "Preparing Sakhi…")
                }
            } else {
                LoginView(viewModel: LoginViewModel(authService: authService))
            }
        }
        .dismissesKeyboardOnTapOutside()
        .animation(.smooth(duration: 0.35), value: authService.isAuthenticated)
        .animation(.smooth(duration: 0.25), value: authService.isLoading)
        .task(id: authService.userId) {
            guard let userId = authService.userId else {
                preparedUserId = nil
                return
            }
            dependencies.prepareCache(for: userId)
            preparedUserId = userId
        }
    }
}
