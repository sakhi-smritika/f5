import Auth
import Foundation
import Observation

@MainActor
@Observable
final class GoalsListViewModel {
    var goals: [Goal] = []
    var loadError: String?
    var showCreate = false
    var newName = ""
    var newDescription = ""
    var newProgress = ""
    var createStatus: SaveStatus = .idle

    private(set) var isRefreshing = false
    private(set) var hasData = false

    /// Only block the list with a spinner when there is nothing cached to show.
    var isLoading: Bool { isRefreshing && !hasData }

    private let authService: AuthService
    private let cache: CacheStore
    private let refreshTracker: SessionRefreshTracker

    init(authService: AuthService, cache: CacheStore, refreshTracker: SessionRefreshTracker) {
        self.authService = authService
        self.cache = cache
        self.refreshTracker = refreshTracker
        readFromCache()
    }

    func appear() async {
        readFromCache()
        guard refreshTracker.claim(RefreshKey.goals) else { return }
        await refresh()
    }

    /// Pull to refresh always goes to the network.
    func reload() async {
        _ = refreshTracker.claim(RefreshKey.goals)
        await refresh()
    }

    private func readFromCache() {
        goals = cache.goals()
        hasData = cache.hasSynced(RefreshKey.goals)
    }

    private func refresh() async {
        isRefreshing = true
        loadError = nil
        defer { isRefreshing = false }

        do {
            let loaded = try await GoalsService.listGoals()
            goals = loaded
            hasData = true
            cache.replaceGoals(loaded)
            cache.markSynced(RefreshKey.goals)
        } catch {
            refreshTracker.release(RefreshKey.goals)
            if !hasData {
                loadError = error.localizedDescription
            }
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
            await refresh()
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

    var loadError: String?
    var saveStatus: SaveStatus = .idle
    var showCreateChild = false
    var childName = ""
    var childDescription = ""
    var childProgress = ""
    var createChildStatus: SaveStatus = .idle
    var didDelete = false

    private(set) var isRefreshing = false
    private(set) var hasData = false

    /// Only block the form with a spinner when there is nothing cached to show.
    var isLoading: Bool { isRefreshing && !hasData }

    /// Guards the editable fields: a background refresh must never overwrite text
    /// the user is in the middle of typing.
    private var hasUnsavedEdits = false

    private let authService: AuthService
    private let cache: CacheStore
    private let refreshTracker: SessionRefreshTracker

    init(
        goalId: UUID,
        authService: AuthService,
        cache: CacheStore,
        refreshTracker: SessionRefreshTracker
    ) {
        self.goalId = goalId
        self.authService = authService
        self.cache = cache
        self.refreshTracker = refreshTracker
        readFromCache()
    }

    func appear() async {
        guard !hasUnsavedEdits else { return }
        readFromCache()
        guard refreshTracker.claim(RefreshKey.goals) else { return }
        await refresh()
    }

    private func readFromCache() {
        let cached = cache.goals()
        guard !cached.isEmpty, let goal = cached.first(where: { $0.id == goalId }) else { return }
        apply(goal, allGoals: cached)
        hasData = true
    }

    private func apply(_ goal: Goal, allGoals: [Goal]) {
        self.allGoals = allGoals
        goalName = goal.goalName
        goalDescription = goal.goalDescription ?? ""
        progress = goal.progress ?? ""
        breadcrumb = GoalsService.breadcrumb(goals: allGoals, goalId: goalId)
        // `listGoals` returns every goal in the same order `childGoals` would, so
        // the children are already here — no second request needed.
        children = allGoals.filter { $0.parentGoal == goalId }
    }

    private func refresh() async {
        isRefreshing = true
        loadError = nil
        defer { isRefreshing = false }

        do {
            let loaded = try await GoalsService.listGoals()
            cache.replaceGoals(loaded)
            cache.markSynced(RefreshKey.goals)

            guard !hasUnsavedEdits else { return }
            if let goal = loaded.first(where: { $0.id == goalId }) {
                apply(goal, allGoals: loaded)
                hasData = true
            } else if let fetched = try await GoalsService.goal(id: goalId) {
                cache.upsertGoal(fetched)
                apply(fetched, allGoals: loaded)
                hasData = true
            } else if !hasData {
                loadError = "Goal not found."
            }
        } catch {
            refreshTracker.release(RefreshKey.goals)
            if !hasData {
                loadError = error.localizedDescription
            }
        }
    }

    func markEdited() {
        hasUnsavedEdits = true
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
            cache.upsertGoal(saved)
            hasUnsavedEdits = false
            hasData = true
            saveStatus = .saved
            await refresh()
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
            await refresh()
        } catch {
            createChildStatus = .error(error.localizedDescription)
        }
    }

    func delete() async {
        do {
            try await GoalsService.delete(id: goalId)
            cache.deleteGoal(id: goalId)
            didDelete = true
        } catch {
            saveStatus = .error(error.localizedDescription)
        }
    }
}
