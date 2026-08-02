import SwiftUI

struct RootView: View {
    @Environment(AuthService.self) private var authService
    @Environment(AppDependencies.self) private var dependencies

    /// View models hydrate from the cache in their initialisers, so the tabs must
    /// not be built until the cache is confirmed to belong to this account.
    @State private var preparedUserId: UUID?

    /// Covers both restoring the session and priming the cache, so startup is a
    /// single uninterrupted splash rather than two separate loading states.
    private var isPreparing: Bool {
        if authService.isLoading { return true }
        guard authService.isAuthenticated else { return false }
        guard let userId = authService.userId else { return true }
        return preparedUserId != userId
    }

    var body: some View {
        Group {
            if isPreparing {
                SplashView()
            } else if authService.isAuthenticated {
                MainTabView()
            } else {
                LoginView(viewModel: LoginViewModel(authService: authService))
            }
        }
        .transition(.opacity)
        .dismissesKeyboardOnTapOutside()
        .animation(.smooth(duration: 0.35), value: isPreparing)
        .animation(.smooth(duration: 0.35), value: authService.isAuthenticated)
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
