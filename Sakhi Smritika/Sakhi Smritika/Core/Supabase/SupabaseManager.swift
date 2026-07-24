import Auth
import Foundation
import Supabase

/// Shared Supabase client. Prefer accessing through `AuthService` / feature services.
enum SupabaseManager {
    static let client: SupabaseClient = {
        // Opt into the upcoming default (see supabase-swift#822 / #844).
        // Must be set on AuthOptions at client creation — otherwise AuthClient
        // reports the "Initial session emitted after attempting to refresh…" issue.
        let authOptions = SupabaseClientOptions.AuthOptions(
            storage: AuthClient.Configuration.defaultLocalStorage,
            emitLocalSessionAsInitialSession: true
        )

        assert(
            authOptions.emitLocalSessionAsInitialSession,
            "emitLocalSessionAsInitialSession must be true"
        )

        return SupabaseClient(
            supabaseURL: AppConfig.supabaseURL,
            supabaseKey: AppConfig.supabasePublishableKey,
            options: .init(auth: authOptions)
        )
    }()
}
