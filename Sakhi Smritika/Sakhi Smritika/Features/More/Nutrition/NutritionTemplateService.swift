import Foundation
import Supabase

enum NutritionTemplateService {
    static func listActive() async throws -> [NutritionTemplate] {
        try await SupabaseManager.client
            .from("nutrition_templates")
            .select()
            .eq("is_active", value: true)
            .order("hour", ascending: true)
            .order("created_at", ascending: true)
            .execute()
            .value
    }

    static func listAll() async throws -> [NutritionTemplate] {
        try await SupabaseManager.client
            .from("nutrition_templates")
            .select()
            .order("hour", ascending: true)
            .order("created_at", ascending: true)
            .execute()
            .value
    }

    static func create(
        hour: Int,
        nutrition: String,
        isActive: Bool,
        userId: UUID
    ) async throws -> NutritionTemplate {
        let payload = NutritionTemplateInsert(
            userId: userId,
            hour: hour,
            nutrition: nutrition,
            isActive: isActive
        )
        return try await SupabaseManager.client
            .from("nutrition_templates")
            .insert(payload)
            .select()
            .single()
            .execute()
            .value
    }

    static func update(
        id: UUID,
        hour: Int,
        nutrition: String,
        isActive: Bool
    ) async throws -> NutritionTemplate {
        let payload = NutritionTemplateUpdate(
            hour: hour,
            nutrition: nutrition,
            isActive: isActive
        )
        return try await SupabaseManager.client
            .from("nutrition_templates")
            .update(payload)
            .eq("id", value: id)
            .select()
            .single()
            .execute()
            .value
    }

    static func delete(id: UUID) async throws {
        try await SupabaseManager.client
            .from("nutrition_templates")
            .delete()
            .eq("id", value: id)
            .execute()
    }
}
