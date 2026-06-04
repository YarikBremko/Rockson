# Using Claude to Build and Modify Web Apps
### A practical guide for non-developers

This guide is based on real experience building the Rockson Performance Schedule App with Claude. It covers what works, what to watch out for, and ready-to-use prompt templates you can copy and adapt.

---

## The golden rule: talk before you build

The single most effective thing you can do is **have a conversation before asking for any code**. Claude works best when it fully understands what you want before writing a single line. If you jump straight to "build me an app that does X", you'll get something that technically works but probably isn't quite right — and fixing a half-built app is harder than building the right one from the start.

A good session looks like this:
1. Describe the idea broadly
2. Answer Claude's clarifying questions
3. Review a mockup or written plan
4. **Then** ask it to start coding

This is exactly how the Schedule App was built — and the mockup step alone saved several rounds of back-and-forth.

---

## Before you start: what to have ready

The more context you give upfront, the better the result. Useful things to have:

- **A description of who uses the app and what they do with it** (e.g. "a PT who creates weekly training schedules for clients")
- **Any design assets** — logo, brand colours, font names. Claude can match a house style if you give it the hex codes and font names.
- **An example of an existing document or output** — if the app produces something (a PDF, a report, a schedule), sharing an example of the current version tells Claude exactly what to aim for.
- **A clear answer on hosting** — will it run on a laptop, a Raspberry Pi, a server? This affects the tech choices.

---

## How to structure your first prompt

Don't try to describe everything in one paragraph. Use sections. Here is a template that works well:

```
I want to build a web app. Here is what I need:

[0. Overview]
One paragraph describing what this app is and who uses it.

[1. Design requirements]
- Any specific visual style, colours, fonts, or logo
- Light/dark mode needs
- Language (e.g. Dutch, English)

[2. Functionality]
List each feature as a numbered point. Be specific about what
each feature does, not just what it is called.

[3. Questions I already have answers to]
Any decisions you have already made (e.g. "it should run on a
Raspberry Pi", "data should be saved between sessions").

[4. What I am not sure about yet]
Things you want Claude's input on before deciding.

Please ask me any clarifying questions before starting to code.
Do not write any code yet — first make sure we agree on the
approach, then show me a mockup or plan.
```

The last two lines are important. They stop Claude from rushing into code before the plan is solid.

---

## Giving Claude your house style

If you want the app to match your branding, give Claude the exact values:

```
The app should match my brand style:
- Primary colour: #f9b233 (gold/amber)
- Background: #0d0d0d (near black)
- Font: Bebas Neue for headings, DM Sans for body text
- No emoji anywhere in the UI
- Tone: clean, professional, minimal
I will attach my logo as an image.
```

Claude can load fonts from Google Fonts automatically — just give it the font names.

---

## Requesting changes to an existing app

When the app is already built and you want to change something, be as specific as possible about **what and where**. Vague requests produce vague results.

**Less effective:**
> "Can you make the PDF look better?"

**More effective:**
> "In the PDF export, the exercise rows are too small when there is a photo attached. I want the row to be taller and the photo to display at roughly 120×120px on the right side of the row. The exercise name, muscle group pill, and notes should stay on the left."

When reporting a bug, always include:
- What you did (the action you took)
- What you expected to happen
- What actually happened
- Any error message shown (copy it exactly, or paste the server log)

**Bug report template:**
```
I found a bug in the app.

What I did: [describe the action step by step]
What I expected: [what should have happened]
What actually happened: [what went wrong]
Error message (if any): [paste exact text]

The relevant file is probably: [app.py / index.html / etc. if you know]
```

---

## Providing the code to Claude

When starting a new session to work on an existing app, always provide the source files. Claude has no memory of previous sessions — each conversation starts fresh.

**How to do this:**
1. Upload the relevant files directly in the chat (drag and drop)
2. Also provide the `TECHNICAL_DOCUMENTATION.md` file — this gives Claude the full picture of how the app works without having to read every line of code

A good opening message for a new session:
```
I have an existing web app called the Rockson Performance Schedule App.
I am attaching the source files and a technical documentation document
that explains how everything works.

I want to make the following change: [describe what you want]

Please read the documentation and the relevant source files before
suggesting any changes.
```

---

## Understanding the files

The Schedule App has three files you will ever need to edit:

| File | What it controls |
|---|---|
| `app.py` | Everything on the server side — data, API, PDF export |
| `templates/index.html` | Everything you see in the browser — layout, buttons, colours |
| `schema.sql` | The database structure — only needed if adding new data fields |

For most visual changes (layout, colours, fonts, adding a button, changing a label) you only need `index.html`. For changes to how data is saved, calculated, or exported you need `app.py`. You will rarely need to touch `schema.sql`.

---

## Getting files back from Claude

After Claude makes a change, it will present the updated file for download. Always download it and replace the file on your server. The SCP command to copy a file to the Raspberry Pi is:

```
scp filename.py user@raspberrypi-ip:/path/to/project/filename.py
```

After copying, restart the app for the changes to take effect.

---

## Useful prompt templates

### "Add a new feature"
```
I want to add a new feature to the app.

Feature description:
[Describe what it does in plain language]

Where it should appear:
[Which screen or section — e.g. "in the schedule builder, below the exercise table"]

How it should work:
[Step by step — what does the user do, what does the app do in response]

Please look at the relevant parts of the code first, then tell me
your plan before making any changes.
```

### "Change how something looks"
```
I want to change the appearance of [element] in [screen/section].

Currently it looks like: [describe or attach a screenshot]
I want it to look like: [describe the desired result]

This is a visual/CSS change only — no backend changes needed.
Please update index.html only.
```

### "Fix a bug"
```
There is a bug in the app.

Steps to reproduce:
1. [step]
2. [step]
3. [step]

Expected result: [what should happen]
Actual result: [what happens instead]
Error message: [paste any error text]

Attached are the relevant source files. Please identify the cause
and fix it.
```

### "Explain how something works"
```
I don't want any code changes. I just want to understand how
[feature/section] works in this app. Please explain it in plain
language, not technical jargon.
```

### "Add a new field to existing data"
```
I want to add a new field called "[field name]" to [clients / exercises / schedules / etc.].

What it stores: [description]
Where it should appear: [in the builder / on the dashboard / in the PDF / etc.]
Data type: [text / number / yes-no / date]

Please tell me which files need to change and what the database
migration command is, before making any changes.
```

---

## Things to keep in mind

**Claude does not remember previous sessions.** Every new conversation starts from scratch. Always attach the source files and documentation when starting a new session.

**Always ask for a plan before code on complex changes.** For anything that touches more than one file, ask Claude to explain what it plans to change before it does it. This catches misunderstandings early.

**Test after every change.** Don't stack multiple changes in one session without testing in between. If something breaks, it's much easier to find if you know which change caused it.

**Keep backups before big changes.** The entire database is one file — `instance/rockson.db`. Copy it before any session that involves structural changes.

**Be specific about what you don't want.** Claude sometimes adds things you didn't ask for. If you want a minimal change, say so explicitly: "Only change what is necessary for this feature. Do not refactor or improve anything else."

**If the result isn't right, describe what's wrong specifically.** "This doesn't look right" gives Claude nothing to work with. "The button is too large and should be the same size as the other buttons in the header" is actionable.
