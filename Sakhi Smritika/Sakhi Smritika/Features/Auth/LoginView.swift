import Observation
import SwiftUI

@MainActor
@Observable
final class LoginViewModel {
    var email = ""
    var password = ""
    var isSubmitting = false
    var errorMessage: String?

    private let authService: AuthService

    init(authService: AuthService) {
        self.authService = authService
    }

    var canSubmit: Bool {
        !email.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty
            && !password.isEmpty
            && !isSubmitting
    }

    func signIn() async {
        guard canSubmit else { return }
        isSubmitting = true
        errorMessage = nil
        defer { isSubmitting = false }

        do {
            try await authService.signIn(email: email, password: password)
        } catch {
            errorMessage = error.localizedDescription
        }
    }
}

struct LoginView: View {
    @Bindable var viewModel: LoginViewModel
    @FocusState private var focusedField: Field?

    private enum Field {
        case email, password
    }

    var body: some View {
        ZStack {
            background

            VStack(spacing: 0) {
                Spacer(minLength: 48)

                VStack(spacing: 12) {
                    Image(systemName: "sparkles")
                        .font(.system(size: 44, weight: .light))
                        .symbolRenderingMode(.hierarchical)
                        .foregroundStyle(.primary)

                    Text("Sakhi Smritika")
                        .font(.largeTitle.weight(.semibold))
                        .tracking(-0.5)

                    Text("Sign in to continue")
                        .font(.subheadline)
                        .foregroundStyle(.secondary)
                }
                .padding(.bottom, 40)

                VStack(spacing: 14) {
                    TextField("Email", text: $viewModel.email)
                        .textContentType(.username)
                        .keyboardType(.emailAddress)
                        .textInputAutocapitalization(.never)
                        .autocorrectionDisabled()
                        .focused($focusedField, equals: .email)
                        .submitLabel(.next)
                        .onSubmit { focusedField = .password }
                        .padding(16)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))

                    SecureField("Password", text: $viewModel.password)
                        .textContentType(.password)
                        .focused($focusedField, equals: .password)
                        .submitLabel(.go)
                        .onSubmit {
                            Task { await viewModel.signIn() }
                        }
                        .padding(16)
                        .background(.regularMaterial, in: RoundedRectangle(cornerRadius: 14, style: .continuous))

                    if let errorMessage = viewModel.errorMessage {
                        Text(errorMessage)
                            .font(.footnote)
                            .foregroundStyle(.red)
                            .frame(maxWidth: .infinity, alignment: .leading)
                            .transition(.opacity)
                    }

                    Button {
                        Task { await viewModel.signIn() }
                    } label: {
                        Group {
                            if viewModel.isSubmitting {
                                ProgressView()
                                    .tint(.white)
                            } else {
                                Text("Sign In")
                                    .fontWeight(.semibold)
                            }
                        }
                        .frame(maxWidth: .infinity)
                        .padding(.vertical, 16)
                    }
                    .buttonStyle(.borderedProminent)
                    .controlSize(.large)
                    .disabled(!viewModel.canSubmit)
                    .sensoryFeedback(.impact(weight: .medium), trigger: viewModel.isSubmitting)
                }
                .padding(.horizontal, 24)

                Spacer()
                Spacer()
            }
        }
        .onAppear { focusedField = .email }
    }

    private var background: some View {
        LinearGradient(
            colors: [
                Color(.systemBackground),
                Color(.systemGray6).opacity(0.85),
                Color(.systemBackground),
            ],
            startPoint: .topLeading,
            endPoint: .bottomTrailing
        )
        .ignoresSafeArea()
    }
}
