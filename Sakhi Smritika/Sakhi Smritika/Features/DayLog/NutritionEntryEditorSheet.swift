import SwiftUI

struct NutritionEntryEditorSheet: View {
    let title: String
    @Binding var hour: Int
    @Binding var food: String
    let onSave: () -> Void
    let onCancel: () -> Void

    var body: some View {
        NavigationStack {
            Form {
                Section("Time") {
                    Picker("Hour", selection: $hour) {
                        ForEach(0..<24, id: \.self) { value in
                            Text(DayLogViewModel.hourLabel(value)).tag(value)
                        }
                    }
                }

                Section("What did you eat?") {
                    TextField("Food or meal…", text: $food, axis: .vertical)
                        .lineLimit(2...6)
                }
            }
            .navigationTitle(title)
            .navigationBarTitleDisplayMode(.inline)
            .toolbar {
                ToolbarItem(placement: .cancellationAction) {
                    Button("Cancel", action: onCancel)
                }
                ToolbarItem(placement: .confirmationAction) {
                    Button("Done", action: onSave)
                        .disabled(food.trimmingCharacters(in: .whitespacesAndNewlines).isEmpty)
                }
            }
        }
        .presentationDetents([.medium])
    }
}
