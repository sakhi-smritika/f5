import SwiftUI

struct RootView: View {
    @Environment(AuthService.self) private var authService

    var body: some View {
        Group {
            if authService.isLoading {
                LoadingView(message: "Preparing Sakhi…")
            } else if authService.isAuthenticated {
                MainTabView()
            } else {
                LoginView(viewModel: LoginViewModel(authService: authService))
            }
        }
        .animation(.smooth(duration: 0.35), value: authService.isAuthenticated)
        .animation(.smooth(duration: 0.25), value: authService.isLoading)
    }
}
