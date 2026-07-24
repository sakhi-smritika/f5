import Auth
import Foundation

extension APIClient {
    func makeURLRequest(
        path: String,
        method: String,
        body: Data? = nil,
        contentType: String? = "application/json",
        accept: String? = nil
    ) -> URLRequest {
        let cleaned = path.hasPrefix("/") ? String(path.dropFirst()) : path
        let url = AppConfig.backendURL.appending(path: cleaned)
        var request = URLRequest(url: url)
        request.httpMethod = method
        request.httpBody = body
        if let contentType, body != nil {
            request.setValue(contentType, forHTTPHeaderField: "Content-Type")
        }
        if let accept {
            request.setValue(accept, forHTTPHeaderField: "Accept")
        }
        if let token = authService.accessToken {
            request.setValue("Bearer \(token)", forHTTPHeaderField: "Authorization")
        }
        return request
    }

    func stream(
        path: String,
        method: String = "POST",
        body: Data?
    ) async throws -> URLSession.AsyncBytes {
        var request = makeURLRequest(
            path: path,
            method: method,
            body: body,
            contentType: "application/json",
            accept: "text/event-stream"
        )
        request.timeoutInterval = 300

        let (bytes, response) = try await URLSession.shared.bytes(for: request)
        guard let http = response as? HTTPURLResponse else {
            throw APIError.network(URLError(.badServerResponse))
        }
        if http.statusCode == 401 {
            await authService.handleUnauthorized()
            throw APIError.unauthorized
        }
        guard (200..<300).contains(http.statusCode) else {
            // Try to read a small error body if available — stream may still yield bytes.
            throw APIError.httpStatus(http.statusCode, nil)
        }
        return bytes
    }

    func uploadMultipart(
        path: String,
        fileData: Data,
        filename: String,
        mimeType: String
    ) async throws -> Data {
        let boundary = "Boundary-\(UUID().uuidString)"
        var body = Data()
        body.append("--\(boundary)\r\n".data(using: .utf8)!)
        body.append(
            "Content-Disposition: form-data; name=\"file\"; filename=\"\(filename)\"\r\n"
                .data(using: .utf8)!
        )
        body.append("Content-Type: \(mimeType)\r\n\r\n".data(using: .utf8)!)
        body.append(fileData)
        body.append("\r\n--\(boundary)--\r\n".data(using: .utf8)!)

        let (data, http) = try await request(
            path: path,
            method: "POST",
            body: body,
            contentType: "multipart/form-data; boundary=\(boundary)"
        )
        try Self.validateSuccess(http, data: data)
        return data
    }
}
