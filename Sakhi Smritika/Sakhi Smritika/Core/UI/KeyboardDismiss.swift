import SwiftUI
import UIKit

/// Marker subclass so the recogniser can be installed at most once per window.
private final class KeyboardDismissTapGesture: UITapGestureRecognizer {}

/// Window-level tap-to-dismiss for the keyboard. SwiftUI's `onTapGesture` is
/// swallowed by scroll views and lists, so the recogniser lives on the `UIWindow`
/// where it sees every touch. `cancelsTouchesInView` stays false so buttons,
/// links and scrolling keep working as normal.
@MainActor
final class KeyboardDismissController: NSObject, UIGestureRecognizerDelegate {
    static let shared = KeyboardDismissController()

    func install(on window: UIWindow?) {
        guard let window else { return }
        guard window.gestureRecognizers?.contains(where: { $0 is KeyboardDismissTapGesture }) != true else { return }

        let tap = KeyboardDismissTapGesture(target: self, action: #selector(handleTap))
        tap.cancelsTouchesInView = false
        tap.delegate = self
        window.addGestureRecognizer(tap)
    }

    @objc private func handleTap(_ recognizer: UITapGestureRecognizer) {
        recognizer.view?.endEditing(true)
    }

    /// Ignore taps that land on a text input: those already move focus, and
    /// dismissing would fight the field that is about to become first responder.
    /// `UITextInput` also covers SwiftUI's private text-editing views.
    func gestureRecognizer(
        _ gestureRecognizer: UIGestureRecognizer,
        shouldReceive touch: UITouch
    ) -> Bool {
        var view = touch.view
        while let current = view {
            if current is UITextInput { return false }
            view = current.superview
        }
        return true
    }

    func gestureRecognizer(
        _ gestureRecognizer: UIGestureRecognizer,
        shouldRecognizeSimultaneouslyWith other: UIGestureRecognizer
    ) -> Bool {
        true
    }
}

private struct KeyboardDismissInstaller: UIViewRepresentable {
    func makeUIView(context: Context) -> UIView {
        let view = UIView(frame: .zero)
        view.isUserInteractionEnabled = false
        return view
    }

    /// The window is only reachable once the view joins the hierarchy, which
    /// happens after `makeUIView` returns.
    func updateUIView(_ uiView: UIView, context: Context) {
        DispatchQueue.main.async {
            KeyboardDismissController.shared.install(on: uiView.window)
        }
    }
}

extension View {
    /// Applied once at the app root: tapping anywhere outside a text field
    /// dismisses the keyboard.
    func dismissesKeyboardOnTapOutside() -> some View {
        background(KeyboardDismissInstaller().frame(width: 0, height: 0))
    }
}
