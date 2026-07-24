import Foundation
import Supabase

enum KbitService {
    static func listKbits(unreadOnly: Bool = false) async throws -> [KnowledgeBit] {
        if unreadOnly {
            return try await SupabaseManager.client
                .from("knowledge_bits")
                .select()
                .eq("is_read", value: false)
                .order("created_at", ascending: false)
                .execute()
                .value
        }
        return try await SupabaseManager.client
            .from("knowledge_bits")
            .select()
            .order("created_at", ascending: false)
            .execute()
            .value
    }

    static func getKbit(id: UUID) async throws -> KnowledgeBit? {
        try await SupabaseManager.client
            .from("knowledge_bits")
            .select()
            .eq("id", value: id)
            .maybeSingle()
            .execute()
            .value
    }

    static func updateKbit(id: UUID, updates: KbitUpdate) async throws {
        try await SupabaseManager.client
            .from("knowledge_bits")
            .update(updates)
            .eq("id", value: id)
            .execute()
    }

    static func discussionMap() async throws -> [UUID: UUID] {
        struct Row: Decodable {
            let id: UUID
            let kbitId: UUID?
            enum CodingKeys: String, CodingKey {
                case id
                case kbitId = "kbit_id"
            }
        }
        let rows: [Row] = try await SupabaseManager.client
            .from("conversations")
            .select("id, kbit_id")
            .execute()
            .value
        var map: [UUID: UUID] = [:]
        for row in rows {
            if let kbitId = row.kbitId {
                map[kbitId] = row.id
            }
        }
        return map
    }

    static func strategies(api: APIClient) async throws -> StrategyCatalog {
        try await api.getJSON("/api/v1/kbits/strategies")
    }

    static func invoke(api: APIClient, body: InvokeKbitsBody) async throws -> [KnowledgeBit] {
        let response: InvokeKbitsResponse = try await api.sendJSON(
            "/api/v1/kbits/invoke",
            method: "POST",
            body: body
        )
        return response.bits
    }

    static func delete(api: APIClient, id: UUID) async throws {
        try await api.sendJSONEmptyBody(
            "/api/v1/kbits/\(id.uuidString.lowercased())",
            method: "DELETE"
        )
    }

    static func ensureDiscussion(api: APIClient, kbitId: UUID) async throws -> UUID {
        let response: EnsureDiscussionResponse = try await api.sendJSON(
            "/api/v1/kbits/\(kbitId.uuidString.lowercased())/discussion",
            method: "POST",
            body: EmptyBody()
        )
        return response.conversationId
    }
}

private struct EmptyBody: Encodable {}
