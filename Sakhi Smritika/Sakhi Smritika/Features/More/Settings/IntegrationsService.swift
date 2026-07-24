import Foundation

struct GoogleConnectionStatus: Decodable, Equatable {
    let connected: Bool
    let googleEmail: String?
    let connectedAt: String?

    enum CodingKeys: String, CodingKey {
        case connected
        case googleEmail = "google_email"
        case connectedAt = "connected_at"
    }
}

private struct GoogleAuthorizeResponse: Decodable {
    let url: String
}

enum IntegrationsService {
    static func googleStatus(api: APIClient) async throws -> GoogleConnectionStatus {
        try await api.getJSON("/api/v1/integrations/google/status")
    }

    static func googleAuthorizeURL(api: APIClient, successRedirect: String) async throws -> URL {
        let response: GoogleAuthorizeResponse = try await api.getJSON(
            "/api/v1/integrations/google/authorize",
            queryItems: [
                URLQueryItem(name: "success_redirect", value: successRedirect),
            ]
        )
        guard let url = URL(string: response.url) else {
            throw APIError.invalidURL
        }
        return url
    }

    static func disconnectGoogle(api: APIClient) async throws {
        try await api.sendJSONEmptyBody("/api/v1/integrations/google", method: "DELETE")
    }
}
