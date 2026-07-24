# Sakhi Smritika (iOS)

SwiftUI iPhone app for Sakhi Smritika. Shares auth, Supabase tables, and FastAPI backend with the web app.

## Requirements

- Xcode 26+
- iOS 26+ Simulator or device
- Local: Supabase (`supabase start`) + FastAPI backend on port 8080

## Environments

| Build | xcconfig | URLs |
|---|---|---|
| **Debug** | `Config/Local.xcconfig` | `http://127.0.0.1:54321` + `:8080` |
| **Release** | `Config/Production.xcconfig` | placeholders — fill before shipping |
| Staging file | `Config/Staging.xcconfig` | placeholders (wire to a Staging scheme when ready) |

Config values are injected into `Config/Info.plist` and read by `AppConfig`.

## Open & run

1. Open `Sakhi Smritika.xcodeproj` in Xcode
2. Wait for SPM to resolve **supabase-swift**
3. Select scheme **Sakhi Smritika** → iPhone Simulator
4. Run (`⌘R`)

Sign in with an existing account (no sign-up on iOS). Seed user from backend seeds: `seed_user@gmail.com` / `password123`.

## Architecture

```
Sakhi Smritika/
├── App/                 # Root, tabs, dependencies
├── Core/                # Config, Auth, Network, Supabase, shared UI
└── Features/            # Auth, Diary, DayLog, Chat, Kbits, More
```

Phase 1 ships: login, glass tab shell (default **Chat**), More (icon-only), placeholders for other features.

Phase 2 ships: **Diary**, **Day Log**, **Profile**, and **Goals** (list + detail with breadcrumbs) via direct Supabase CRUD.

Phase 3 ships: **Chat** — conversation list (new / folders / chats), lazy create on first send, SSE streaming, model picker, photo/file attachments, client date/time/timezone/location context.

Phase 4 ships: **Kbits** — Instagram Reels-style vertical pager, in-card scroll for long content, generate + strategies, interactions, discussion bottom sheet.

Phase 5 ships: **Settings** — Google Calendar/Tasks connect & disconnect via `ASWebAuthenticationSession`. Callback scheme: `sakhi-smritika://oauth` (allowlisted in the backend alongside the web success redirect).
