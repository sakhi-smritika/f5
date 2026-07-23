# Philosophy

The beliefs that shape every screen, flow, and tool in Sakhi Smritika. If you
understand this page, the rest of the product should feel inevitable.

## 1. Reflection precedes growth

You cannot change what you never notice. The product's center of gravity is the
**diary and day log** — not because journaling is trendy, but because a written
trace of your days is the raw material for every insight that follows. Goals
without reflection become wishful lists; reflection without goals becomes a
diary that goes nowhere. The product deliberately holds both.

## 2. The companion should *remember*

The name says it: *Sakhi* (a friend) *Smritika* (of memory). A companion that
forgets you every conversation is a search box with manners. The intent is a
companion that can look at your actual diary, your real goals, and the knowledge
you've saved — and speak to *your* life, not a generic one.

Today that memory is mostly the current conversation plus your profile; deeper,
durable memory is a direction the product is built to grow into. The principle
holds regardless: **personalization comes from your own data, not from guessing.**

## 3. Your data is yours, and the system knows it

Every row belongs to exactly one person. The product is built so that one user
can never see another's life. This is not a feature bolted on later — it is a
constraint the architecture is designed around (see
[flows/05-data-and-trust.md](flows/05-data-and-trust.md)). Trust is the
precondition for honesty, and honesty is the precondition for growth.

## 4. Read freely, write carefully

The companion is encouraged to *read* your data whenever it helps — that's how it
becomes relevant. But **writing** to your life (logging a day, changing a goal,
saving knowledge) is a heavier act. The design principle: the assistant should
confirm before it writes, and always tell you plainly what it changed. Your
record of your own life should never be altered behind your back.

## 5. Don't guess — look

When the assistant is asked about your Tuesday, it should *read Tuesday*, not
invent a plausible Tuesday. Tools exist so the model can ground its answers in
truth. A confident hallucination about your own life is worse than "I don't have
an entry for that day."

## 6. Small surface, honest boundaries

The product would rather do a few things truthfully than many things vaguely.
When something isn't available (Google not connected, no entry for a date, a
feature not built yet), the honest response is to say so — not to paper over it.
Each flow doc has an explicit **"what this deliberately does not do"** section for
exactly this reason.

## 7. Knowledge should be relevant, not abundant

The internet has infinite content. The **Knowledge Bits** feature is opinionated:
it generates a *small* number of pieces tied to *your* goals, then screens and
ranks them so you see what matters to you — not an endless feed. Growth comes
from applying a few right ideas, not from drowning in many.

## 8. The product is a loop, not a destination

Reflect → Understand → Intend → Learn → and back to reflect. There is no "done."
The design favors returning: today's entry, this week's goal check-in, a new bit
to try. Features earn their place by feeding the loop.

---

*These principles describe intent, not implementation. The code is the source of
truth for what actually happens.*
