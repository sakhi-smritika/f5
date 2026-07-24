import SwiftUI

@main
struct Sakhi_SmritikaApp: App {
    @State private var dependencies = AppDependencies()

    var body: some Scene {
        WindowGroup {
            RootView()
                .environment(dependencies)
                .environment(dependencies.authService)
        }
    }
}
