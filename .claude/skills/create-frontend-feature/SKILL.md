---
name: create-frontend-feature
description: Workflow for creating feature components, API helpers, pages, and route constants in client/ using feature-first architecture.
---

# Create Frontend Feature Skill

Follow this workflow when building or expanding a frontend feature in `client/`.

## Step 1: Create Feature Directory Structure
Locate or create your feature folder inside `client/src/features/<feature_name>/`:
```text
client/src/features/<feature_name>/
├── api/          # Typed API helper functions
├── components/   # Feature-specific UI components
├── pages/        # Main page components (if applicable)
├── types/        # Feature TypeScript interfaces
└── context/      # React contexts (if state is shared)
```

## Step 2: Define TypeScript Models & Interfaces
Define clear request/response models in `types/` or `client/interfaces/`:
```typescript
export interface FeatureItem {
  id: string;
  title: string;
  createdAt: string;
}

export interface CreateFeaturePayload {
  title: string;
}
```

## Step 3: Implement Typed API Helpers
Create API functions using the shared Axios client in `api/<feature>Api.ts` or `client/lib/functions/`:
- Use relative backend paths (`/api/...` or `/auth/...`).
- Let the central Axios interceptor manage JWT Bearer headers and token auto-refresh.

```typescript
import { http } from "@shared/api/http";
import { FeatureItem, CreateFeaturePayload } from "../types";

export const fetchFeatureItems = async (): Promise<FeatureItem[]> => {
  const response = await http.get("/api/feature-items");
  return response.data;
};

export const createFeatureItem = async (payload: CreateFeaturePayload): Promise<FeatureItem> => {
  const response = await http.post("/api/feature-items", payload);
  return response.data;
};
```

## Step 4: Add UI Components
Build modular, typed React components using Tailwind CSS and design tokens from `client/src/shared/ui/quizwerk.ts`:
- Ensure proper accessibility attributes (`aria-*`, `role`).
- Handle loading, empty, and error states gracefully.

## Step 5: Register Route in Pages Router
For user-accessible pages, create a page under `client/pages/`:
1. Add route path constant in `client/constants/patterns/routes.ts` or `@shared/config/patterns/routes`.
2. Export the page from `client/pages/<route_name>.tsx`:

```tsx
export { default } from "@features/<feature_name>/pages/<FeaturePage>";
```

3. Wrap with `RequireAuth` if the page requires authentication.

## Step 6: Verify Build & Types
Run `pnpm exec tsc --noEmit` and `pnpm lint` in `client/` to verify zero type regressions.
