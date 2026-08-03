import Auth
import Foundation
import Observation

@MainActor
@Observable
final class NutritionTemplatesViewModel {
    var templates: [NutritionTemplate] = []
    var loadError: String?
    var createStatus: SaveStatus = .idle
    var showCreate = false

    var newHour = Calendar.current.component(.hour, from: Date())
    var newNutrition = ""
    var newIsActive = true

    var editingTemplate: NutritionTemplate?
    var editHour = 0
    var editNutrition = ""
    var editIsActive = true
    var editStatus: SaveStatus = .idle

    private(set) var isLoading = false

    private let authService: AuthService

    init(authService: AuthService) {
        self.authService = authService
    }

    func appear() async {
        await reload()
    }

    func reload() async {
        isLoading = true
        loadError = nil
        defer { isLoading = false }

        do {
            templates = try await NutritionTemplateService.listAll()
        } catch {
            loadError = error.localizedDescription
        }
    }

    func create() async {
        guard let userId = authService.user?.id else {
            createStatus = .error("You must be signed in.")
            return
        }

        let nutrition = newNutrition.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !nutrition.isEmpty else {
            createStatus = .error("Enter what you usually eat.")
            return
        }

        createStatus = .saving
        do {
            let created = try await NutritionTemplateService.create(
                hour: newHour,
                nutrition: nutrition,
                isActive: newIsActive,
                userId: userId
            )
            templates.append(created)
            templates.sort { lhs, rhs in
                if lhs.hour != rhs.hour { return lhs.hour < rhs.hour }
                return (lhs.createdAt ?? "") < (rhs.createdAt ?? "")
            }
            newNutrition = ""
            newIsActive = true
            showCreate = false
            createStatus = .saved
        } catch {
            createStatus = .error(error.localizedDescription)
        }
    }

    func beginEdit(_ template: NutritionTemplate) {
        editingTemplate = template
        editHour = template.hour
        editNutrition = template.nutrition
        editIsActive = template.isActive
        editStatus = .idle
    }

    func saveEdit() async {
        guard let template = editingTemplate else { return }

        let nutrition = editNutrition.trimmingCharacters(in: .whitespacesAndNewlines)
        guard !nutrition.isEmpty else {
            editStatus = .error("Enter what you usually eat.")
            return
        }

        editStatus = .saving
        do {
            let updated = try await NutritionTemplateService.update(
                id: template.id,
                hour: editHour,
                nutrition: nutrition,
                isActive: editIsActive
            )
            if let index = templates.firstIndex(where: { $0.id == template.id }) {
                templates[index] = updated
            }
            templates.sort { lhs, rhs in
                if lhs.hour != rhs.hour { return lhs.hour < rhs.hour }
                return (lhs.createdAt ?? "") < (rhs.createdAt ?? "")
            }
            editingTemplate = nil
            editStatus = .saved
        } catch {
            editStatus = .error(error.localizedDescription)
        }
    }

    func delete(_ template: NutritionTemplate) async {
        do {
            try await NutritionTemplateService.delete(id: template.id)
            templates.removeAll { $0.id == template.id }
        } catch {
            loadError = error.localizedDescription
        }
    }
}
