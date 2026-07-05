# ADR 004 — Frontend Architecture: React + Zustand + React Router

**Date:** 2026-07-05  
**Status:** Accepted  
**Context:** M4 — Polish & Demo

---

## Context

VERIDA needed a frontend that is:
1. **PWA-installable** (mobile-first, offline-capable)
2. **Fast** — sub-2s TTI on mid-range mobile
3. **Small team maintainable** — minimal boilerplate, strong TypeScript
4. **Incrementally deliverable** — lazy-loadable pages, small vendor bundle

## Decision

### React 18 + TypeScript + Vite

- React 18 concurrent features (Suspense for lazy loading) match the progressive disclosure UX
- TypeScript strict mode — all pages and API clients are fully typed
- Vite builds in < 1s dev, < 1s prod; PWA plugin via `vite-plugin-pwa` (Workbox)

### React Router v6

- Declarative nested routing with `<Outlet />` pattern — clean layout nesting (`RequireAuth > Layout > Page`)
- `lazy()` + `<Suspense>` per-page splits: each page chunk is 2–9 KB gzipped
- No file-system router — explicit route map kept in `App.tsx` for clarity

### Zustand for state management (not Redux)

**Why not Redux:**
- Redux requires actions + reducers + selectors + middleware per feature — 5× the boilerplate for a small app
- Redux Toolkit reduces boilerplate but still requires slices, thunks, and selectors
- For VERIDA's scope (2 global stores: auth + feed), Redux overhead is not justified

**Why Zustand:**
- Single function `create()` — no provider, no context boilerplate
- `persist()` middleware for token storage in 3 lines
- Direct state access in components without `connect()` or `useSelector` chains
- Typed with TypeScript generics — no `any` needed
- Bundle: ~3 KB gzipped (vs Redux Toolkit ~16 KB)

### Axios for API client

- Interceptors for JWT attach + auto-refresh on 401 in one place
- Consistent with backend's REST conventions
- Alternative (fetch) would require manual retry logic and error normalization

### Tailwind CSS v3

- Utility-first → predictable dark/light mode via `prefers-color-scheme` + manual toggle
- `dark:` variant throughout — no CSS-in-JS runtime cost
- Single accent: `indigo-500/600` — consistent brand color
- JIT purges unused classes → minimal CSS bundle

### PWA strategy

- `vite-plugin-pwa` generates Workbox service worker
- Precache: all JS/CSS/HTML/icons (262 KB)
- Runtime: NetworkFirst for `/api/` calls (10s timeout), CacheFirst for assets
- `manifest.json`: `display: standalone`, `orientation: portrait`, themed icons

## Consequences

- **Bundle:** vendor chunk 164 KB raw / 53 KB gzipped (React + ReactDOM + Router). Acceptable for PWA install baseline.
- **No SSR:** Not needed for MVP; can add with Vite SSR or Remix later
- **No global loading state:** Each page manages its own loading state — simpler than a global loading reducer
- **Zustand devtools:** Not included in production build (tree-shaken)
- **React Query considered:** Would simplify caching/pagination but adds ~15 KB and is overkill for VERIDA's simple feed pagination pattern

## Alternatives considered

| Option | Reason rejected |
|--------|----------------|
| Next.js | SSR complexity not needed; Vite faster for pure SPA PWA |
| Redux Toolkit | Too much boilerplate for 2 stores; Zustand does the same in 1/5th the code |
| Jotai | Atom model is less familiar; Zustand's slice pattern matches team conventions |
| SWR | Useful but adds complexity; Zustand manual fetch is sufficient for MVP |
| Vue 3 / Svelte | Team has React expertise; consistency with ecosystem |
