import Auth
import Foundation
import Observation
import Supabase

@MainActor
@Observable
final class AuthService {
    private(set) var session: Session?
    private(set) var isLoading = true
    private(set) var lastError: String?

    /// User is signed in only when a non-expired session exists.
    /// Required when using `emitLocalSessionAsInitialSession: true`.
    var isAuthenticated: Bool {
        guard let session else { return false }
        return !session.isExpired
    }

    var user: User? { isAuthenticated ? session?.user : nil }
    var accessToken: String? { isAuthenticated ? session?.accessToken : nil }

    /// Lets callers identify the account without importing the Supabase `Auth` module.
    var userId: UUID? { user?.id }

    /// Runs only for a user-initiated log out, not for an expired token, so a
    /// transient 401 does not throw away the local cache.
    @ObservationIgnored
    var onExplicitSignOut: (@MainActor () -> Void)?

    @ObservationIgnored
    private var authListenerTask: Task<Void, Never>?

    init() {
        startListening()
    }

    func startListening() {
        authListenerTask?.cancel()
        authListenerTask = Task { [weak self] in
            guard let self else { return }

            // Prefer authStateChanges only — the SDK always emits `.initialSession`
            // first. Avoid an extra `auth.session` await that races the listener.
            for await (event, session) in SupabaseManager.client.auth.authStateChanges {
                guard !Task.isCancelled else { break }
                handle(event: event, session: session)
            }
        }
    }

    func signIn(email: String, password: String) async throws {
        lastError = nil
        do {
            let session = try await SupabaseManager.client.auth.signIn(
                email: email.trimmingCharacters(in: .whitespacesAndNewlines),
                password: password
            )
            self.session = session
            isLoading = false
        } catch {
            lastError = error.localizedDescription
            throw error
        }
    }

    func signOut(clearLocalData: Bool = true) async {
        lastError = nil
        do {
            try await SupabaseManager.client.auth.signOut()
            session = nil
        } catch {
            lastError = error.localizedDescription
            session = nil
        }
        if clearLocalData {
            onExplicitSignOut?()
        }
    }

    /// Called by `APIClient` on 401 responses.
    func handleUnauthorized() async {
        await signOut(clearLocalData: false)
    }

    private func handle(event: AuthChangeEvent, session: Session?) {
        switch event {
        case .initialSession:
            // With emitLocalSessionAsInitialSession, this may be an expired
            // cached session. Keep loading until refresh succeeds or we sign out.
            self.session = session
            if let session, session.isExpired {
                isLoading = true
            } else {
                isLoading = false
            }

        case .tokenRefreshed, .signedIn, .userUpdated:
            self.session = session
            isLoading = false

        case .signedOut:
            self.session = nil
            isLoading = false

        default:
            self.session = session
            isLoading = false
        }
    }
}
