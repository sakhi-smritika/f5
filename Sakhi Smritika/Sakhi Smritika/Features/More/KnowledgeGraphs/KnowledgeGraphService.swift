import Foundation
import Supabase

enum KnowledgeGraphService {
    static func listGraphs() async throws -> [KnowledgeGraph] {
        try await SupabaseManager.client
            .from("knowledge_graphs")
            .select()
            .order("created_at", ascending: false)
            .execute()
            .value
    }

    static func create(
        title: String,
        description: String?,
        firstNodeLabel: String,
        userId: UUID
    ) async throws -> KnowledgeGraph {
        let graph: KnowledgeGraph = try await SupabaseManager.client
            .from("knowledge_graphs")
            .insert(
                KnowledgeGraphInsert(
                    title: title,
                    description: description?.nilIfEmpty,
                    userId: userId
                )
            )
            .select()
            .single()
            .execute()
            .value

        _ = try await SupabaseManager.client
            .from("knowledge_nodes")
            .insert(
                KnowledgeNodeInsert(
                    graphId: graph.id,
                    label: firstNodeLabel.trimmingCharacters(in: .whitespacesAndNewlines)
                )
            )
            .execute()

        return graph
    }

    static func delete(id: UUID) async throws {
        try await SupabaseManager.client
            .from("knowledge_graphs")
            .delete()
            .eq("id", value: id)
            .execute()
    }
}

private extension String {
    var nilIfEmpty: String? {
        trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            ? nil
            : trimmingCharacters(in: .whitespacesAndNewlines)
    }
}
