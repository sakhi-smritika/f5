import Foundation
import Supabase

enum ProfileService {
    static func profile(userId: UUID) async throws -> Profile? {
        try await SupabaseManager.client
            .from("users")
            .select("id, username, display_name, full_name, user_information, system_instructions, created_at, updated_at")
            .eq("id", value: userId)
            .maybeSingle()
            .execute()
            .value
    }

    static func update(
        userId: UUID,
        fullName: String,
        userInformation: String,
        systemInstructions: String
    ) async throws -> Profile {
        let payload = ProfileUpdate(
            fullName: fullName.trimmingCharacters(in: .whitespacesAndNewlines).nilIfEmpty,
            userInformation: userInformation.trimmingCharacters(in: .whitespacesAndNewlines).nilIfEmpty,
            systemInstructions: systemInstructions.trimmingCharacters(in: .whitespacesAndNewlines).nilIfEmpty
        )
        return try await SupabaseManager.client
            .from("users")
            .update(payload)
            .eq("id", value: userId)
            .select("id, username, display_name, full_name, user_information, system_instructions, created_at, updated_at")
            .single()
            .execute()
            .value
    }
}

private extension String {
    var nilIfEmpty: String? {
        isEmpty ? nil : self
    }
}
