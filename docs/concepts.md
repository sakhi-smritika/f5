# Concepts & Vocabulary

Shared words, defined once. When these docs say "Goal" or "Bit," this is what
they mean.

## Diary

A person's record of a **day**. There is at most one diary entry per person per
date. An entry holds a few kinds of reflection:

- **How was the day** — the overall felt sense of the day.
- **Major events** — the notable things that happened.
- **General content** — free-form journaling, anything else.
- **Day Log** — the hour-by-hour breakdown (see below).

Think of the diary as the *narrative* layer of a day.

## Day Log

The **hourly** layer of a day: 24 slots (hour `0` through `23`), each a short note
of what you were doing. Where the diary answers "how was today?", the day log
answers "where did today actually go?". It lives inside the same day's diary
entry.

## Goal

Something a person is intending toward. Goals form a **hierarchy** — a goal can
have sub-goals (a parent/child tree), so a large intention ("get healthier") can
break into smaller ones ("sleep by 11", "walk daily"). A goal carries a name, an
optional description, and a free-text **progress** note that evolves over time.

## Knowledge Bit ("Bit")

A short, self-contained piece of knowledge — a tip, insight, or idea — usually
**tied to one of your goals**. Bits are generated for you, then curated: you can
mark them read, like/dislike them, and rate them. The intent is a *small, relevant*
stream of things worth trying, not an infinite feed. Bits can also be created
directly (by you, or by the companion on your behalf).

## Sakhi (the companion / the agent)

The conversational companion at the heart of the app. Sakhi can **read** your
diary, day logs, goals, and bits, and — with your confirmation — **write** to them
(log a day, update a goal's progress, save a bit). It can also connect to your
**Google Calendar and Tasks** when you link your account. Sakhi is not a generic
chatbot; its whole value is that it speaks to *your* recorded life.

The word for the companion's abilities is **tools** — each tool is one concrete
thing Sakhi can do (e.g. "read a diary entry", "create a goal"). See
[flows/04-the-agent.md](flows/04-the-agent.md).

## Profile

The stable facts about a person: their name, background, and any **custom
instructions** for how the companion should behave. Unlike diary/goals, the
profile is always available to Sakhi as context — it doesn't need a tool to read
it.

## Two ways data moves

Two words that recur in the flow docs:

- **Direct (client → Supabase):** simple, personal CRUD (reading your diary,
  editing a goal) goes straight from the app to the database, scoped to you by
  **Row Level Security**.
- **Backend (client → server → data):** anything that needs server-side logic or
  privileged access — the companion's chat, generating bits, Google integration —
  goes through the backend, which re-checks that you own what you're touching.

Why this split matters is covered in
[flows/05-data-and-trust.md](flows/05-data-and-trust.md).

---

*These definitions describe intent, not implementation. The code is the source of
truth for what actually happens.*
