import Observation
import SwiftUI

/// App-wide dependencies. Injected once at the root.
@MainActor
@Observable
final class AppDependencies {
    let authService: AuthService
    let apiClient: APIClient

    init() {
        let auth = AuthService()
        self.authService = auth
        self.apiClient = APIClient(authService: auth)
    }
}
