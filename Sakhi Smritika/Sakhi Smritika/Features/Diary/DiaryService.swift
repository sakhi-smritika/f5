import Foundation
import Supabase

enum DiaryService {
    static func entry(for date: String) async throws -> DiaryEntry? {
        try await SupabaseManager.client
            .from("diary")
            .select()
            .eq("date", value: date)
            .maybeSingle()
            .execute()
            .value
    }

    static func saveDiary(
        date: String,
        howWasTheDay: String,
        majorEvents: String,
        generalContent: String,
        userId: UUID
    ) async throws -> DiaryEntry {
        let payload = DiaryUpsert(
            date: date,
            userId: userId,
            howWasTheDay: howWasTheDay,
            majorEvents: majorEvents,
            generalContent: generalContent
        )
        return try await SupabaseManager.client
            .from("diary")
            .upsert(payload, onConflict: "user_id,date")
            .select()
            .single()
            .execute()
            .value
    }

    static func saveDayLog(
        date: String,
        dayLog: [String: String],
        nutritionEntries: [NutritionEntry],
        userId: UUID
    ) async throws -> DiaryEntry {
        let payload = DiaryUpsert(
            date: date,
            userId: userId,
            dayLog: dayLog,
            nutritionEntries: nutritionEntries
        )
        return try await SupabaseManager.client
            .from("diary")
            .upsert(payload, onConflict: "user_id,date")
            .select()
            .single()
            .execute()
            .value
    }
}
