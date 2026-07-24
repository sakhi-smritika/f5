import Auth
import Foundation
import Observation

@MainActor
@Observable
final class GoalsListViewModel {
    var goals: [Goal] = []
    var isLoading = true
    var loadError: String?
    var showCreate = false
    var newName = ""
    var newDescription = ""
    var newProgress = ""
    var createStatus: SaveStatus = .idle

    private let authService: AuthService

    init(authService: AuthService) {
        self.authService = authService
    }

    func load() async {
        isLoading = true
        loadError = nil
        defer { isLoading = false }

        do {
            goals = try await GoalsService.listGoals()
        } catch {
            loadError = error.localizedDescription
        }
    }

    func create() async {
        guard let userId = authService.user?.id else {
            createStatus = .error("You must be signed in.")
            return
        }
        let name = newName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else {
            createStatus = .error("Goal name is required.")
            return
        }

        createStatus = .saving
        do {
            _ = try await GoalsService.create(
                name: name,
                description: newDescription,
                progress: newProgress,
                parentGoal: nil,
                userId: userId
            )
            newName = ""
            newDescription = ""
            newProgress = ""
            showCreate = false
            createStatus = .idle
            await load()
        } catch {
            createStatus = .error(error.localizedDescription)
        }
    }

    func parentName(for goal: Goal) -> String? {
        guard let parentId = goal.parentGoal else { return nil }
        return goals.first(where: { $0.id == parentId })?.goalName
    }
}

@MainActor
@Observable
final class GoalDetailViewModel {
    let goalId: UUID

    var goalName = ""
    var goalDescription = ""
    var progress = ""
    var children: [Goal] = []
    var breadcrumb: [Goal] = []
    var allGoals: [Goal] = []

    var isLoading = true
    var loadError: String?
    var saveStatus: SaveStatus = .idle
    var showCreateChild = false
    var childName = ""
    var childDescription = ""
    var childProgress = ""
    var createChildStatus: SaveStatus = .idle
    var didDelete = false

    private let authService: AuthService

    init(goalId: UUID, authService: AuthService) {
        self.goalId = goalId
        self.authService = authService
    }

    func load() async {
        isLoading = true
        loadError = nil
        defer { isLoading = false }

        do {
            allGoals = try await GoalsService.listGoals()
            let goal: Goal
            if let cached = allGoals.first(where: { $0.id == goalId }) {
                goal = cached
            } else if let fetched = try await GoalsService.goal(id: goalId) {
                goal = fetched
            } else {
                loadError = "Goal not found."
                return
            }
            goalName = goal.goalName
            goalDescription = goal.goalDescription ?? ""
            progress = goal.progress ?? ""
            breadcrumb = GoalsService.breadcrumb(goals: allGoals, goalId: goalId)
            children = try await GoalsService.childGoals(parentId: goalId)
        } catch {
            loadError = error.localizedDescription
        }
    }

    func markEdited() {
        if saveStatus != .idle { saveStatus = .idle }
    }

    func save() async {
        let name = goalName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else {
            saveStatus = .error("Goal name is required.")
            return
        }
        saveStatus = .saving
        do {
            let saved = try await GoalsService.update(
                id: goalId,
                name: name,
                description: goalDescription,
                progress: progress
            )
            goalName = saved.goalName
            goalDescription = saved.goalDescription ?? ""
            progress = saved.progress ?? ""
            saveStatus = .saved
            await load()
        } catch {
            saveStatus = .error(error.localizedDescription)
        }
    }

    func createChild() async {
        guard let userId = authService.user?.id else {
            createChildStatus = .error("You must be signed in.")
            return
        }
        let name = childName.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !name.isEmpty else {
            createChildStatus = .error("Goal name is required.")
            return
        }
        createChildStatus = .saving
        do {
            _ = try await GoalsService.create(
                name: name,
                description: childDescription,
                progress: childProgress,
                parentGoal: goalId,
                userId: userId
            )
            childName = ""
            childDescription = ""
            childProgress = ""
            showCreateChild = false
            createChildStatus = .idle
            await load()
        } catch {
            createChildStatus = .error(error.localizedDescription)
        }
    }

    func delete() async {
        do {
            try await GoalsService.delete(id: goalId)
            didDelete = true
        } catch {
            saveStatus = .error(error.localizedDescription)
        }
    }
}
