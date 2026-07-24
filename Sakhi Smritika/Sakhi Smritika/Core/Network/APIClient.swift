import Auth
import Foundation

enum APIError: LocalizedError {
    case invalidURL
    case unauthorized
    case httpStatus(Int, String?)
    case decoding(Error)
    case network(Error)

    var errorDescription: String? {
        switch self {
        case .invalidURL:
            return "Invalid request URL."
        case .unauthorized:
            return "Your session expired. Please sign in again."
        case .httpStatus(let code, let body):
            if let body, !body.isEmpty {
                return "Request failed (\(code)): \(body)"
            }
            return "Request failed with status \(code)."
        case .decoding(let error):
            return "Could not read the server response: \(error.localizedDescription)"
        case .network(let error):
            return error.localizedDescription
        }
    }
}

/// Thin HTTP client mirroring the web `apiFetch` helper.
@MainActor
final class APIClient {
    let authService: AuthService
    let session: URLSession

    init(authService: AuthService, session: URLSession = .shared) {
        self.authService = authService
        self.session = session
    }

    func request(
        path: String,
        method: String = "GET",
        queryItems: [URLQueryItem]? = nil,
        body: Data? = nil,
        contentType: String? = "application/json"
    ) async throws -> (Data, HTTPURLResponse) {
        let cleaned = path.hasPrefix("/") ? String(path.dropFirst()) : path
        var components = URLComponents(
            url: AppConfig.backendURL.appending(path: cleaned),
            resolvingAgainstBaseURL: false
        )
        if let queryItems, !queryItems.isEmpty {
            components?.queryItems = queryItems
        }
        guard let url = components?.url else {
            throw APIError.invalidURL
        }
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body

        if let contentType, body != nil {
            request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }
        if let token = authService.accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }

        do {
            let (data, response) = try await session.data(for: request)
            guard let http = response as? HTTPURLResponse else {
                throw APIError.network(URLError(.badServerResponse))
            }
            if http.statusCode == 401 {
                await authService.handleUnauthorized()
                throw APIError.unauthorized
            }
            return (data, http)
        } catch let error as APIError {
            throw error
        } catch {
            throw APIError.network(error)
        }
    }

    func getJSON<T: Decodable>(
        _ path: String,
        queryItems: [URLQueryItem]? = nil,
        as type: T.Type = T.self
    ) async throws -> T {
        let (data, http) = try await request(path: path, queryItems: queryItems)
        try Self.validateSuccess(http, data: data)
        do {
            return try JSONDecoder.api.decode(type, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func sendJSON<T: Decodable, Body: Encodable>(
        _ path: String,
        method: String,
        body: Body,
        as type: T.Type = T.self
    ) async throws -> T {
        let encoded = try JSONEncoder.api.encode(body)
        let (data, http) = try await request(path: path, method: method, body: encoded)
        try Self.validateSuccess(http, data: data)
        do {
            return try JSONDecoder.api.decode(type, from: data)
        } catch {
            throw APIError.decoding(error)
        }
    }

    func sendJSONEmptyBody(_ path: String, method: String) async throws {
        let (data, http) = try await request(path: path, method: method)
        try Self.validateSuccess(http, data: data)
    }

    static func validateSuccess(_ http: HTTPURLResponse, data: Data) throws {
        guard (200..<300).contains(http.statusCode) else {
            let body = String(data: data, encoding: .utf8)
            throw APIError.httpStatus(http.statusCode, body)
        }
    }
}

extension JSONEncoder {
    static let api: JSONEncoder = {
        let encoder = JSONEncoder()
        // Types use explicit snake_case CodingKeys — do not also convert.
        return encoder
    }()
}

extension JSONDecoder {
    static let api: JSONDecoder = {
        let decoder = JSONDecoder()
        // Types use explicit snake_case CodingKeys — do not also convert
        // (convertFromSnakeCase + snake CodingKeys causes "data is missing").
        return decoder
    }()
}
