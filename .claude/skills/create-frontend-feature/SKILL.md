---
name: create-frontend-feature
description: Complete workflow for creating or extending Next.js feature modules, API helpers, UI components, pages router integration, and Jest tests in client/.
---

# Create Frontend Feature Skill

Follow this workflow when building or expanding frontend features in `client/`.

## Step 1: Feature Directory Organization
Locate or create your feature directory under `client/src/features/<feature_name>/`:
```text
client/src/features/<feature_name>/
├── api/          # Typed API helper functions
├── components/   # React UI components
├── pages/        # Feature view pages
├── types/        # TypeScript interfaces & models
└── context/      # React contexts (if shared state is needed)
```

## Step 2: Define TypeScript Interfaces
Define strict types for API payloads and component props in `types/` or `client/interfaces/`:
```typescript
export interface QuizItem {
  id: string;
  title: string;
  category: string;
  questionCount: number;
}
```

## Step 3: Implement Typed API Helpers
Create API functions in `api/<feature>Api.ts` using the central Axios client (`@shared/api/http`):
- Do not manually attach `Authorization` headers; the Axios interceptor handles JWT token injection and auto-refresh on 401.

```typescript
import { http } from "@shared/api/http";
import { QuizItem } from "../types";

export const getFeatureQuizzes = async (): Promise<QuizItem[]> => {
  const response = await http.get("/api/feature-quizzes");
  return response.data;
};
```

## Step 4: Build Accessible React Components
Construct components using Tailwind CSS and tokens from `client/src/shared/ui/quizwerk.ts`:
- Ensure proper accessibility attributes (`aria-*`, `role`).
- Handle loading, error, and empty states.

## Step 5: Mount Route in Pages Router
For new pages:
1. Define route path constant in `client/constants/patterns/routes.ts` or `@shared/config/patterns/routes`.
2. Create page entry in `client/pages/<route_name>.tsx`:

```tsx
export { default } from "@features/<feature_name>/pages/<FeaturePage>";
```

3. Wrap with `RequireAuth` if the page requires authentication.

## Step 6: Verify Type Safety & Linting
Execute type check and linting from `client/`:
```bash
pnpm exec tsc --noEmit
pnpm lint
```
