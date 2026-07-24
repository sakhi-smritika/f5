import Auth
import CoreLocation
import Foundation
import Supabase

private extension UUID {
    /// Backend / Postgres seed IDs are lowercase; Swift's `uuidString` is uppercase.
    var apiString: String { uuidString.lowercased() }
}

enum ChatService {
    // MARK: - Supabase (list / folders)

    static func listConversations() async throws -> [Conversation] {
        try await SupabaseManager.client
            .from("conversations")
            .select("id, title, folder_id, created_at, updated_at, kbit_id")
            .order("updated_at", ascending: false)
            .execute()
            .value
    }

    static func listFolders() async throws -> [ChatFolder] {
        try await SupabaseManager.client
            .from("chat_folder")
            .select("id, name, created_at, updated_at")
            .order("name", ascending: true)
            .execute()
            .value
    }

    static func createFolder(name: String, userId: UUID) async throws -> ChatFolder {
        let payload = ChatFolderInsert(name: name.trimmingCharacters(in: .whitespacesAndNewlines), userId: userId)
        return try await SupabaseManager.client
            .from("chat_folder")
            .insert(payload)
            .select("id, name, created_at, updated_at")
            .single()
            .execute()
            .value
    }

    static func renameFolder(id: UUID, name: String) async throws -> ChatFolder {
        let payload = ChatFolderRename(name: name.trimmingCharacters(in: .whitespacesAndNewlines))
        return try await SupabaseManager.client
            .from("chat_folder")
            .update(payload)
            .eq("id", value: id)
            .select("id, name, created_at, updated_at")
            .single()
            .execute()
            .value
    }

    // MARK: - Backend REST

    static func listModels(api: APIClient) async throws -> ChatModelsResponse {
        try await api.getJSON("/api/v1/models")
    }

    static func createConversation(api: APIClient, folderId: UUID? = nil) async throws -> CreateConversationResponse {
        try await api.sendJSON(
            "/api/v1/chat/conversations",
            method: "POST",
            body: CreateConversationBody(folderId: folderId)
        )
    }

    static func loadMessages(api: APIClient, conversationId: UUID) async throws -> [ChatMessage] {
        let response: MessagesResponse = try await api.getJSON(
            "/api/v1/chat/conversations/\(conversationId.apiString)/messages"
        )
        return response.messages
    }

    static func renameConversation(api: APIClient, id: UUID, title: String) async throws {
        struct Response: Decodable { let id: UUID; let title: String? }
        let _: Response = try await api.sendJSON(
            "/api/v1/chat/conversations/\(id.apiString)",
            method: "PATCH",
            body: UpdateConversationBody(title: title)
        )
    }

    static func moveConversation(api: APIClient, id: UUID, folderId: UUID?) async throws {
        struct Response: Decodable { let id: UUID; let folderId: UUID?
            enum CodingKeys: String, CodingKey {
                case id
                case folderId = "folder_id"
            }
        }
        var body = UpdateConversationBody()
        if let folderId {
            body.folderId = folderId
        } else {
            body.clearFolder = true
        }
        let _: Response = try await api.sendJSON(
            "/api/v1/chat/conversations/\(id.apiString)",
            method: "PATCH",
            body: body
        )
    }

    static func deleteConversation(api: APIClient, id: UUID) async throws {
        try await api.sendJSONEmptyBody(
            "/api/v1/chat/conversations/\(id.apiString)",
            method: "DELETE"
        )
    }

    static func deleteFolder(api: APIClient, id: UUID) async throws {
        try await api.sendJSONEmptyBody(
            "/api/v1/chat/folders/\(id.apiString)",
            method: "DELETE"
        )
    }

    static func uploadAttachment(
        api: APIClient,
        conversationId: UUID,
        data: Data,
        filename: String,
        mimeType: String
    ) async throws -> ChatAttachment {
        let raw = try await api.uploadMultipart(
            path: "/api/v1/chat/conversations/\(conversationId.apiString)/attachments",
            fileData: data,
            filename: filename,
            mimeType: mimeType
        )
        return try JSONDecoder.api.decode(ChatAttachment.self, from: raw)
    }

    static func deleteAttachment(api: APIClient, conversationId: UUID, attachmentId: UUID) async throws {
        try await api.sendJSONEmptyBody(
            "/api/v1/chat/conversations/\(conversationId.apiString)/attachments/\(attachmentId.apiString)",
            method: "DELETE"
        )
    }

    @MainActor
    static func streamMessage(
        api: APIClient,
        conversationId: UUID,
        text: String,
        model: String?,
        attachmentIds: [UUID],
        onDelta: @escaping @MainActor (String) -> Void,
        onDone: @escaping @MainActor (String?) -> Void,
        onError: @escaping @MainActor (String) -> Void
    ) async {
        let context = ClientContext.current()
        let location = await ClientContext.locationLabel()

        var body = SendMessageBody(
            text: text,
            model: model,
            clientDate: context.date,
            clientTime: context.time,
            clientTimezone: context.timezone,
            clientLocation: location
        )
        if !attachmentIds.isEmpty {
            body.attachmentIds = attachmentIds
        }

        do {
            let encoded = try JSONEncoder.api.encode(body)
            let bytes = try await api.stream(
                path: "/api/v1/chat/conversations/\(conversationId.apiString)/messages",
                body: encoded
            )
            for try await event in SSEStreamReader.events(from: bytes) {
                switch event {
                case .delta(let text):
                    onDelta(text)
                case .done(let title):
                    onDone(title)
                    return
                case .error(let message):
                    onError(message)
                    return
                case .unknown:
                    continue
                }
            }
            onDone(nil)
        } catch {
            onError(error.localizedDescription)
        }
    }
}

enum ClientContext {
    struct Clock {
        let date: String
        let time: String
        let timezone: String?
    }

    private static var cachedLocation: String?
    private static var didAskLocation = false
    private static var activeLocationRequest: LocationOneShot?

    static func current(calendar: Calendar = .current) -> Clock {
        let now = Date()
        let date = DateHelpers.string(from: now, calendar: calendar)
        let comps = calendar.dateComponents([.hour, .minute], from: now)
        let time = String(format: "%02d:%02d", comps.hour ?? 0, comps.minute ?? 0)
        let timezone = TimeZone.current.identifier
        return Clock(date: date, time: time, timezone: timezone)
    }

    static func locationLabel() async -> String? {
        if let cachedLocation { return cachedLocation }
        guard !didAskLocation else { return nil }
        didAskLocation = true

        guard let coordinate = await requestCoordinate() else { return nil }
        if let label = await reverseGeocode(coordinate) {
            cachedLocation = label
            return label
        }
        return nil
    }

    private static func requestCoordinate() async -> CLLocationCoordinate2D? {
        await withCheckedContinuation { continuation in
            let request = LocationOneShot()
            activeLocationRequest = request
            request.request { coordinate in
                activeLocationRequest = nil
                continuation.resume(returning: coordinate)
            }
        }
    }

    private static func reverseGeocode(_ coordinate: CLLocationCoordinate2D) async -> String? {
        let urlString =
            "https://api.bigdatacloud.net/data/reverse-geocode-client?latitude=\(coordinate.latitude)&longitude=\(coordinate.longitude)&localityLanguage=en"
        guard let url = URL(string: urlString) else { return nil }
        do {
            let (data, _) = try await URLSession.shared.data(from: url)
            guard let json = try JSONSerialization.jsonObject(with: data) as? [String: Any] else {
                return nil
            }
            let parts = [
                json["locality"] as? String,
                json["city"] as? String,
                json["principalSubdivision"] as? String,
                json["countryName"] as? String,
            ]
            .compactMap { $0?.trimmingCharacters(in: .whitespacesAndNewlines) }
            .filter { !$0.isEmpty }

            var unique: [String] = []
            for part in parts where !unique.contains(part) {
                unique.append(part)
            }
            return unique.isEmpty ? nil : unique.joined(separator: ", ")
        } catch {
            return nil
        }
    }
}

/// One-shot location helper (keeps CLLocationManager alive until callback).
private final class LocationOneShot: NSObject, CLLocationManagerDelegate {
    private let manager = CLLocationManager()
    private var completion: ((CLLocationCoordinate2D?) -> Void)?

    func request(completion: @escaping (CLLocationCoordinate2D?) -> Void) {
        self.completion = completion
        manager.delegate = self
        manager.desiredAccuracy = kCLLocationAccuracyHundredMeters

        switch manager.authorizationStatus {
        case .notDetermined:
            manager.requestWhenInUseAuthorization()
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        default:
            finish(nil)
        }
    }

    func locationManagerDidChangeAuthorization(_ manager: CLLocationManager) {
        switch manager.authorizationStatus {
        case .authorizedAlways, .authorizedWhenInUse:
            manager.requestLocation()
        case .denied, .restricted:
            finish(nil)
        default:
            break
        }
    }

    func locationManager(_ manager: CLLocationManager, didUpdateLocations locations: [CLLocation]) {
        finish(locations.first?.coordinate)
    }

    func locationManager(_ manager: CLLocationManager, didFailWithError error: Error) {
        finish(nil)
    }

    private func finish(_ coordinate: CLLocationCoordinate2D?) {
        completion?(coordinate)
        completion = nil
    }
}
