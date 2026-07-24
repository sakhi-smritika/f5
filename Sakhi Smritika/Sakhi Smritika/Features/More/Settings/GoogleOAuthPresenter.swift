import AuthenticationServices
import UIKit

/// Presents Google's consent page and resumes when the backend redirects to our custom scheme.
@MainActor
final class GoogleOAuthPresenter: NSObject, ASWebAuthenticationPresentationContextProviding {
    private var session: ASWebAuthenticationSession?

    func authenticate(url: URL, callbackScheme: String) async throws -> URL {
        try await withCheckedThrowingContinuation { continuation in
            let session = ASWebAuthenticationSession(
                url: url,
                callbackURLScheme: callbackScheme
            ) { callbackURL, error in
                Task { @MainActor in
                    self.session = nil
                    if let error {
                        let nsError = error as NSError
                        if nsError.domain == ASWebAuthenticationSessionErrorDomain,
                           nsError.code == ASWebAuthenticationSessionError.canceledLogin.rawValue {
                            continuation.resume(throwing: CancellationError())
                            return
                        }
                        continuation.resume(throwing: error)
                        return
                    }
                    guard let callbackURL else {
                        continuation.resume(throwing: APIError.network(URLError(.badServerResponse)))
                        return
                    }
                    continuation.resume(returning: callbackURL)
                }
            }
            session.presentationContextProvider = self
            session.prefersEphemeralWebBrowserSession = false
            self.session = session
            if !session.start() {
                self.session = nil
                continuation.resume(throwing: APIError.network(URLError(.unknown)))
            }
        }
    }

    func presentationAnchor(for session: ASWebAuthenticationSession) -> ASPresentationAnchor {
        if let window = Self.keyWindow() {
            return window
        }

        let scenes = UIApplication.shared.connectedScenes.compactMap { $0 as? UIWindowScene }
        let scene = scenes.first { $0.activationState == .foregroundActive } ?? scenes.first

        if let window = scene?.windows.first {
            return window
        }
        if let scene {
            return UIWindow(windowScene: scene)
        }

        // Running app should always have a scene; fall back keeps the protocol satisfied.
        preconditionFailure("No UIWindowScene available for OAuth presentation")
    }

    private static func keyWindow() -> UIWindow? {
        UIApplication.shared.connectedScenes
            .compactMap { $0 as? UIWindowScene }
            .flatMap(\.windows)
            .first { $0.isKeyWindow }
    }
}
