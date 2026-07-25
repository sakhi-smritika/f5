import MarkdownUI
import SwiftUI
import WebKit

/// Assistant reply renderer.
/// - While streaming or for plain replies → MarkdownUI (native, fast).
/// - Completed replies containing LaTeX → one WKWebView (markdown-it + KaTeX)
///   so inline math stays inside the sentence.
struct ChatMarkdownView: View {
    let text: String
    var isStreaming: Bool = false

    @Environment(\.colorScheme) private var colorScheme

    var body: some View {
        let display = text.isEmpty && isStreaming ? "…" : text
        // WebView reloads on every streamed delta are wasteful and can flash
        // blank; render math only once the reply is complete.
        if !isStreaming && Self.containsMath(display) {
            ChatRichWebView(text: display, isDark: colorScheme == .dark)
                .frame(maxWidth: .infinity, alignment: .leading)
        } else {
            nativeMarkdown(display)
        }
    }

    @ViewBuilder
    private func nativeMarkdown(_ content: String) -> some View {
        Markdown(content)
            .markdownTheme(.basic)
            .markdownTextStyle(\.text) {
                ForegroundColor(.primary)
            }
            .markdownTextStyle(\.link) {
                ForegroundColor(.accentColor)
            }
            .markdownBlockStyle(\.codeBlock) { configuration in
                configuration.label
                    .markdownTextStyle {
                        FontFamilyVariant(.monospaced)
                        FontSize(.em(0.9))
                    }
                    .padding(10)
                    .background(Color.primary.opacity(0.06), in: RoundedRectangle(cornerRadius: 8))
            }
            .textSelection(.enabled)
            .frame(maxWidth: .infinity, alignment: .leading)
    }

    private static func containsMath(_ text: String) -> Bool {
        text.contains("$$")
            || text.contains("\\[")
            || text.contains("\\(")
            || text.contains("\\begin{")
            || containsInlineDollarMath(text)
    }

    /// A lone `$` (e.g. "$5 budget") shouldn't trigger the WebView; require a
    /// plausible `$...$` pair on one line.
    private static func containsInlineDollarMath(_ text: String) -> Bool {
        guard let regex = try? NSRegularExpression(pattern: #"\$[^\s$][^$\n]*\$"#) else { return false }
        let range = NSRange(text.startIndex..<text.endIndex, in: text)
        return regex.firstMatch(in: text, range: range) != nil
    }
}

// MARK: - Full-message markdown + KaTeX

private struct ChatRichWebView: View {
    let text: String
    let isDark: Bool
    @State private var height: CGFloat = 40

    var body: some View {
        RichContentWebView(text: text, isDark: isDark, height: $height)
            .frame(height: max(height, 40))
            .frame(maxWidth: .infinity, alignment: .leading)
    }
}

private struct RichContentWebView: UIViewRepresentable {
    let text: String
    let isDark: Bool
    @Binding var height: CGFloat

    // Gives the document a real secure origin; some WebKit paths misbehave
    // with the null (about:blank) origin when loading remote CSS/JS.
    private static let baseURL = URL(string: "https://chat.sakhismritika.local/")

    func makeCoordinator() -> Coordinator {
        Coordinator(height: $height)
    }

    func makeUIView(context: Context) -> WKWebView {
        let userController = WKUserContentController()
        userController.add(context.coordinator, name: "height")
        userController.add(context.coordinator, name: "log")
        let config = WKWebViewConfiguration()
        config.userContentController = userController

        let webView = WKWebView(frame: .zero, configuration: config)
        webView.isOpaque = false
        webView.backgroundColor = .clear
        webView.scrollView.isScrollEnabled = false
        webView.scrollView.backgroundColor = .clear
        webView.scrollView.contentInsetAdjustmentBehavior = .never
        webView.navigationDelegate = context.coordinator
        webView.loadHTMLString(Self.html(text: text, isDark: isDark), baseURL: Self.baseURL)
        context.coordinator.lastKey = "\(text.hashValue)|\(isDark)"
        return webView
    }

    func updateUIView(_ webView: WKWebView, context: Context) {
        let key = "\(text.hashValue)|\(isDark)"
        guard context.coordinator.lastKey != key else { return }
        context.coordinator.lastKey = key
        webView.loadHTMLString(Self.html(text: text, isDark: isDark), baseURL: Self.baseURL)
    }

    static func dismantleUIView(_ webView: WKWebView, coordinator: Coordinator) {
        webView.configuration.userContentController.removeScriptMessageHandler(forName: "height")
        webView.configuration.userContentController.removeScriptMessageHandler(forName: "log")
    }

    final class Coordinator: NSObject, WKScriptMessageHandler, WKNavigationDelegate {
        var height: Binding<CGFloat>
        var lastKey: String?

        init(height: Binding<CGFloat>) {
            self.height = height
        }

        func userContentController(
            _ userContentController: WKUserContentController,
            didReceive message: WKScriptMessage
        ) {
            switch message.name {
            case "height":
                guard let value = message.body as? Double else { return }
                let next = CGFloat(value)
                DispatchQueue.main.async {
                    if abs(self.height.wrappedValue - next) > 1 {
                        self.height.wrappedValue = next
                    }
                }
            case "log":
                #if DEBUG
                print("[ChatRichWebView] \(message.body)")
                #endif
            default:
                break
            }
        }

        func webView(_ webView: WKWebView, didFinish navigation: WKNavigation!) {
            webView.evaluateJavaScript("window.reportHeight && window.reportHeight();") { _, _ in }
        }

        func webView(
            _ webView: WKWebView,
            didFailProvisionalNavigation navigation: WKNavigation!,
            withError error: Error
        ) {
            #if DEBUG
            print("[ChatRichWebView] navigation failed: \(error.localizedDescription)")
            #endif
        }
    }

    private static func html(text: String, isDark: Bool) -> String {
        let bodyJSON = jsonString(text)
        let color = isDark ? "#F2F2F7" : "#1C1C1E"
        let muted = isDark ? "#8E8E93" : "#6C6C70"
        let codeBg = isDark ? "rgba(255,255,255,0.08)" : "rgba(0,0,0,0.06)"
        let border = isDark ? "rgba(255,255,255,0.12)" : "rgba(0,0,0,0.1)"

        return """
        <!DOCTYPE html>
        <html>
        <head>
          <meta charset="utf-8">
          <meta name="viewport" content="width=device-width, initial-scale=1, maximum-scale=1">
          <link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.css">
          <style>
            html, body {
              margin: 0;
              padding: 0;
              background: transparent !important;
              color: \(color);
              font-family: -apple-system, system-ui, sans-serif;
              font-size: 16px;
              line-height: 1.45;
              -webkit-text-size-adjust: 100%;
            }
            #content { word-wrap: break-word; overflow-wrap: anywhere; }
            #content > :first-child { margin-top: 0; }
            #content > :last-child { margin-bottom: 0; }
            p { margin: 0 0 0.7em; }
            h1,h2,h3,h4 { margin: 0.9em 0 0.4em; line-height: 1.25; font-weight: 600; }
            h1 { font-size: 1.25em; }
            h2 { font-size: 1.15em; }
            h3 { font-size: 1.05em; }
            ul, ol { margin: 0 0 0.7em; padding-left: 1.35em; }
            li { margin: 0.2em 0; }
            strong { font-weight: 600; }
            a { color: #0A84FF; }
            code {
              font-family: ui-monospace, Menlo, monospace;
              font-size: 0.9em;
              background: \(codeBg);
              padding: 0.1em 0.35em;
              border-radius: 4px;
            }
            pre {
              background: \(codeBg);
              border: 1px solid \(border);
              border-radius: 10px;
              padding: 10px 12px;
              overflow-x: auto;
              margin: 0 0 0.7em;
            }
            pre code { background: transparent; padding: 0; }
            blockquote {
              margin: 0 0 0.7em;
              padding-left: 0.8em;
              border-left: 3px solid \(border);
              color: \(muted);
            }
            .katex-display { margin: 0.6em 0; overflow-x: auto; overflow-y: hidden; }
            .katex { font-size: 1.05em; }
          </style>
        </head>
        <body>
          <div id="content"></div>
          <script>
            const source = \(bodyJSON);

            function log(msg) {
              try { window.webkit.messageHandlers.log.postMessage(String(msg)); } catch (e) {}
            }
            window.onerror = function (msg, src, line) { log('js error: ' + msg + ' @' + line); };

            function reportHeight() {
              const el = document.getElementById('content');
              const h = Math.ceil(el.getBoundingClientRect().height) + 2;
              try { window.webkit.messageHandlers.height.postMessage(h); } catch (e) {}
            }
            window.reportHeight = reportHeight;

            // Never leave the message blank: show plain text until libs render.
            function renderPlain() {
              const el = document.getElementById('content');
              el.textContent = source;
              el.style.whiteSpace = 'pre-wrap';
              reportHeight();
            }

            function renderRich() {
              const md = window.markdownit({ html: false, linkify: true, breaks: false });
              const el = document.getElementById('content');
              el.style.whiteSpace = '';
              el.innerHTML = md.render(source);
              window.renderMathInElement(el, {
                delimiters: [
                  { left: '$$', right: '$$', display: true },
                  { left: '\\\\[', right: '\\\\]', display: true },
                  { left: '$', right: '$', display: false },
                  { left: '\\\\(', right: '\\\\)', display: false }
                ],
                throwOnError: false,
                strict: 'ignore',
                ignoredTags: ['script', 'noscript', 'style', 'textarea', 'pre', 'code']
              });
              reportHeight();
              setTimeout(reportHeight, 120);
              setTimeout(reportHeight, 400);
            }

            function loadScript(src) {
              return new Promise(function (resolve, reject) {
                const s = document.createElement('script');
                s.src = src;
                s.onload = resolve;
                s.onerror = function () { reject(new Error('failed: ' + src)); };
                document.head.appendChild(s);
              });
            }

            renderPlain();
            Promise.all([
              loadScript('https://cdn.jsdelivr.net/npm/markdown-it@14.1.0/dist/markdown-it.min.js'),
              loadScript('https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/katex.min.js')
            ]).then(function () {
              return loadScript('https://cdn.jsdelivr.net/npm/katex@0.16.21/dist/contrib/auto-render.min.js');
            }).then(function () {
              try { renderRich(); } catch (e) { log('render error: ' + e.message); renderPlain(); }
            }).catch(function (e) {
              log(e.message + ' (keeping plain text)');
            });

            if (window.ResizeObserver) {
              new ResizeObserver(reportHeight).observe(document.getElementById('content'));
            }
            window.addEventListener('load', reportHeight);
          </script>
        </body>
        </html>
        """
    }

    private static func jsonString(_ value: String) -> String {
        if let data = try? JSONEncoder().encode([value]),
           let wrapped = String(data: data, encoding: .utf8),
           wrapped.hasPrefix("["), wrapped.hasSuffix("]") {
            return String(wrapped.dropFirst().dropLast())
        }
        return "\"\""
    }
}
