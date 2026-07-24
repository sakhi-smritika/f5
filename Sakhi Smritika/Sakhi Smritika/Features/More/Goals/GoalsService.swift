import Foundation
import Supabase

enum GoalsService {
    static func listGoals() async throws -> [Goal] {
        try await SupabaseManager.client
            .from("goals")
            .select()
            .order("created_at", ascending: false)
            .execute()
            .value
    }

    static func goal(id: UUID) async throws -> Goal? {
        try await SupabaseManager.client
            .from("goals")
            .select()
            .eq("id", value: id)
            .maybeSingle()
            .execute()
            .value
    }

    static func childGoals(parentId: UUID) async throws -> [Goal] {
        try await SupabaseManager.client
            .from("goals")
            .select()
            .eq("parent_goal", value: parentId)
            .order("created_at", ascending: false)
            .execute()
            .value
    }

    static func create(
        name: String,
        description: String?,
        progress: String?,
        parentGoal: UUID?,
        userId: UUID
    ) async throws -> Goal {
        let payload = GoalInsert(
            goalName: name,
            goalDescription: description?.nilIfEmpty,
            progress: progress?.nilIfEmpty,
            parentGoal: parentGoal,
            userId: userId
        )
        return try await SupabaseManager.client
            .from("goals")
            .insert(payload)
            .select()
            .single()
            .execute()
            .value
    }

    static func update(
        id: UUID,
        name: String,
        description: String,
        progress: String
    ) async throws -> Goal {
        let payload = GoalUpdate(
            goalName: name,
            goalDescription: description.nilIfEmpty,
            progress: progress.nilIfEmpty
        )
        return try await SupabaseManager.client
            .from("goals")
            .update(payload)
            .eq("id", value: id)
            .select()
            .single()
            .execute()
            .value
    }

    static func delete(id: UUID) async throws {
        try await SupabaseManager.client
            .from("goals")
            .delete()
            .eq("id", value: id)
            .execute()
    }

    static func breadcrumb(goals: [Goal], goalId: UUID) -> [Goal] {
        let byId = Dictionary(uniqueKeysWithValues: goals.map { ($0.id, $0) })
        var trail: [Goal] = []
        var current = byId[goalId]
        while let goal = current {
            trail.insert(goal, at: 0)
            if let parentId = goal.parentGoal {
                current = byId[parentId]
            } else {
                current = nil
            }
        }
        return trail
    }
}

private extension String {
    var nilIfEmpty: String? {
        trimmingCharacters(in: .whitespacesAndNewlines).isEmpty ? nil : trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
