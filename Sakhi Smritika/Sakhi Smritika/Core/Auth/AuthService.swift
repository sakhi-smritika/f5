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

    func signOut() async {
        lastError = nil
        do {
            try await SupabaseManager.client.auth.signOut()
            session = nil
        } catch {
            lastError = error.localizedDescription
            session = nil
        }
    }

    /// Called by `APIClient` on 401 responses.
    func handleUnauthorized() async {
        await signOut()
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
