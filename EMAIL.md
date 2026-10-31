Subject: AI Software Engineering Intern — RouteMind project

Hi Cubiktech team,

I'm applying for the AI Software Engineering Intern role. I built RouteMind, a route-planning web app that turns plain-English trip descriptions into optimised routes on an interactive map.

**What it does**

You type something like:
> "Start from Railway Station at 9am. Deliver to Mananchira after 10am, Beach by 12pm, Medical College by 4pm. Return to start."

RouteMind reads the text, finds the optimal stop order (respecting time windows), and shows the route on a Leaflet map with arrival/wait/depart times at every stop.

**How I used AI**

I used Claude as the natural-language layer — it reads the free-form trip text and extracts a structured list of stops with time windows. I deliberately kept Claude out of the routing logic: a dynamic-programming solver (Held-Karp algorithm) handles optimisation, so the AI can't produce an invalid plan or skip a stop.

Working with Claude in this project taught me a clear principle: **AI is excellent at understanding ambiguous human language; deterministic algorithms are better for guaranteeing correctness.** Splitting these responsibilities made the app more reliable.

[What *I* personally decided / changed — fill in 1–2 real things you did yourself, e.g. the fallback regex parser you tested, the colour scheme you picked, a bug you fixed, a stop you added to the offline table, etc.]

**Links**

- GitHub: <YOUR_GITHUB_REPO_URL>
- Live demo: <YOUR_RENDER_URL>  (or: "runs locally — happy to share a screen recording")

**Stack**

Python / Flask · Anthropic Claude API · Held-Karp DP solver · Leaflet.js · OpenStreetMap / Nominatim · Render (deployment)

I'm available to walk through the code or the algorithm whenever works for you.

<YOUR_NAME>
<YOUR_EMAIL> | <YOUR_PHONE>
