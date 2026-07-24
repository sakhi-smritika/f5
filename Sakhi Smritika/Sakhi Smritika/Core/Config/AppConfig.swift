import Foundation

/// Runtime configuration sourced from xcconfig → Info.plist.
enum AppConfig {
    enum Environment: String {
        case local = "Local"
        case staging = "Staging"
        case production = "Production"
    }

    static var environment: Environment {
        let raw = Bundle.main.object(forInfoDictionaryKey: "APP_ENVIRONMENT") as? String
        return Environment(rawValue: raw ?? "") ?? .local
    }

    static var supabaseURL: URL {
        guard
            let string = Bundle.main.object(forInfoDictionaryKey: "SUPABASE_URL") as? String,
            let url = URL(string: string),
            !string.contains("YOUR_")
        else {
            preconditionFailure("SUPABASE_URL is missing or still a placeholder in Info.plist / xcconfig")
        }
        return url
    }

    static var supabasePublishableKey: String {
        guard
            let key = Bundle.main.object(forInfoDictionaryKey: "SUPABASE_PUBLISHABLE_KEY") as? String,
            !key.isEmpty,
            !key.contains("YOUR_")
        else {
            preconditionFailure("SUPABASE_PUBLISHABLE_KEY is missing or still a placeholder")
        }
        return key
    }

    static var backendURL: URL {
        guard
            let string = Bundle.main.object(forInfoDictionaryKey: "BACKEND_URL") as? String,
            let url = URL(string: string),
            !string.contains("example.com"),
            !string.contains("YOUR_")
        else {
            preconditionFailure("BACKEND_URL is missing or still a placeholder in Info.plist / xcconfig")
        }
        return url
    }

    /// Custom URL scheme registered in Info.plist for Google OAuth return.
    static let oauthCallbackScheme = "sakhi-smritika"

    /// Backend redirects here after Google consent (`ASWebAuthenticationSession`).
    static let oauthSuccessRedirect = "sakhi-smritika://oauth"
}
