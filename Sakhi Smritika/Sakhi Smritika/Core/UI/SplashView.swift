import SwiftUI

/// Mirrors the `UILaunchScreen` exactly — same background colour, same logo at
/// the same size and position — so the hand-off from the system launch image to
/// the first SwiftUI frame is invisible. Only the caption animates in, and only
/// once startup has taken long enough for a spinner to be reassuring rather than
/// a flicker.
struct SplashView: View {
    var message: String = "Preparing Sakhi…"

    /// Natural size of the `LaunchLogo` asset, which the launch screen centres.
    private static let logoSize: CGFloat = 171

    @State private var showsCaption = false

    var body: some View {
        ZStack {
            Color(.launchBackground)
                .ignoresSafeArea()

            Image(.launchLogo)
                .resizable()
                .scaledToFit()
                .frame(width: Self.logoSize, height: Self.logoSize)
        }
        .overlay(alignment: .bottom) {
            caption
                .opacity(showsCaption ? 1 : 0)
                .padding(.bottom, 64)
        }
        .animation(.easeOut(duration: 0.4), value: showsCaption)
        .task {
            try? await Task.sleep(for: .milliseconds(600))
            showsCaption = true
        }
        // The launch background is black in both appearances, so the status bar
        // needs light content even when the device is in light mode.
        .preferredColorScheme(.dark)
        .accessibilityElement(children: .ignore)
        .accessibilityLabel(message)
    }

    private var caption: some View {
        VStack(spacing: 12) {
            ProgressView()
                .tint(.white.opacity(0.7))

            Text(message)
                .font(.footnote)
                .foregroundStyle(.white.opacity(0.7))
        }
    }
}

#Preview {
    SplashView()
}
