# API Documentation

**Base URL:** `http://localhost:8000`

**Authentication:** Most endpoints require a JWT token. Include in headers: `Authorization: Bearer <your_token>`

---

## Health
System status endpoints.

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/health/dbhealth` | Check database connection |
| POST | `/health/seed-database` | Seed database with test data (dev only) |
| POST | `/health/restore-database` | Restore database from backup |

---

## Authentication
User registration, login, and profile management.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/auth/register` | Create new user account | No |
| POST | `/auth/verify-otp` | Verify email with OTP code | No |
| GET | `/auth/verify-link` | Verify email with link token | No |
| POST | `/auth/resend-verification` | Resend verification email | No |
| POST | `/auth/login` | Login and get JWT token | No |
| POST | `/auth/refresh` | Refresh expired JWT token | No |
| GET | `/auth/profile` | Get current user profile | Yes |
| PUT | `/auth/profile` | Update user profile | Yes |
| POST | `/auth/email-change/request` | Request email change | Yes |
| POST | `/auth/email-change/verify` | Verify email change | Yes |
| DELETE | `/auth/account` | Delete user account | Yes |
| POST | `/auth/request-password-reset` | Request password reset email | No |
| POST | `/auth/reset-password` | Reset password with token | No |
| POST | `/auth/logout` | Logout and invalidate token | Yes |
| GET | `/auth/ping` | Check if auth service is running | No |

---

## Quizzes
Generate, retrieve, and manage quizzes.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/generate-quiz` | Generate AI-powered quiz from topic | Yes |
| POST | `/quizzes/test/create-quiz` | Create new quiz (test) | Yes |
| GET | `/quizzes/test/get-quiz/{quiz_id}` | Get quiz by ID | Yes |
| PUT | `/quizzes/test/update-quiz/{quiz_id}` | Update existing quiz | Yes |
| DELETE | `/quizzes/test/delete-quiz/{quiz_id}` | Delete quiz | Yes |
| GET | `/api/get-questions` | Get quiz questions | No |
| POST | `/api/grade-answers` | Submit and grade user answers | No |
| POST | `/download-quiz` | Download quiz in various formats | Yes |

---

## Folders
Organize quizzes into folders.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/folders/create` | Create new folder | Yes |
| GET | `/api/folders/` | Get all folders for current user | Yes |
| GET | `/api/folders/view/{folder_id}` | Get folder by ID with contents | Yes |
| PUT | `/api/folders/{folder_id}/rename` | Rename folder | Yes |
| DELETE | `/api/folders/{folder_id}` | Delete folder | Yes |
| POST | `/api/folders/bulk_delete` | Delete multiple folders | Yes |
| POST | `/api/folders/{folder_id}/add_quiz` | Add quiz to folder | Yes |
| DELETE | `/api/folders/{folder_id}/remove/{quiz_id}` | Remove quiz from folder | Yes |
| POST | `/api/folders/move_quiz` | Move quiz between folders | Yes |
| POST | `/api/folders/{folder_id}/bulk_remove` | Remove multiple quizzes from folder | Yes |

---

## Saved Quizzes
User's saved quiz library.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/saved-quizzes/` | List all saved quizzes | Yes |
| POST | `/api/saved-quizzes/` | Save a quiz to library | Yes |
| GET | `/api/saved-quizzes/{quiz_id}` | Get saved quiz by ID | Yes |
| DELETE | `/api/saved-quizzes/{quiz_id}` | Remove saved quiz | Yes |
| PATCH | `/api/saved-quizzes/{quiz_id}/rename` | Rename saved quiz | Yes |

---

## Quiz History
Track user's quiz attempts and results.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/quiz-history` | Get user's quiz attempt history | Yes |
| GET | `/api/quiz-history/{history_id}` | Get specific history entry | Yes |
| DELETE | `/api/quiz-history/{history_id}` | Delete history entry | Yes |
| GET | `/get-user-quiz-history` | Alternative history endpoint | Yes |

---

## Live Quiz
Real-time multiplayer quiz sessions.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| POST | `/api/v1/quizzes/{quiz_id}/access-code` | Generate access code for quiz | Yes |
| GET | `/api/v1/quizzes/access/{code}` | Validate access code | No |
| POST | `/api/v1/quizzes/access/{code}/start` | Start live quiz session | No |
| GET | `/api/v1/live-quiz-sessions/{session_id}` | Get session details | No |
| POST | `/api/v1/live-quiz-sessions/{session_id}/answers` | Submit answer for live quiz | No |
| POST | `/api/v1/live-quiz-sessions/{session_id}/submit` | Submit entire session | No |
| GET | `/api/v1/quizzes/{quiz_id}/live-sessions` | List all sessions for quiz | Yes |

---

## Share
Share quizzes with others.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/share/get-quiz-id` | Get random quiz ID | No |
| GET | `/share/share-quiz/{quiz_id}` | Generate shareable link | Yes |
| GET | `/share/shared-quiz/{quiz_id}` | Get shared quiz data (public) | No |
| POST | `/share/share-email` | Share quiz via email | Yes |

---

## Notifications
User notification system.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/notifications/` | Get user notifications | Yes |
| POST | `/api/notifications/` | Create notification (admin) | Yes |
| POST | `/api/notifications/broadcast` | Broadcast to all users (admin) | Yes |
| PUT | `/api/notifications/read-all` | Mark all notifications as read | Yes |
| PUT | `/api/notifications/{notification_id}/read` | Mark single notification as read | Yes |
| DELETE | `/api/notifications/{notification_id}` | Delete notification | Yes |

---

## Categories
Browse quiz categories.

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/categories` | Get all quiz categories | No |
| GET | `/api/category/{category}/subcategories` | Get subcategories | No |
| GET | `/api/category/{category}/subcategory/{subcategory}/types` | Get question types | No |
| GET | `/api/category/{category}/subcategory/{subcategory}/type/{question_type}` | Get quizzes by category | No |

---

## Token Management

| Method | Endpoint | Description | Auth Required |
|--------|----------|-------------|---------------|
| GET | `/api/user/token` | Fetch user token | Yes |
| POST | `/api/user/token` | Add/refresh token | Yes |

---

## Utilities

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/ping-redis` | Check Redis connection |
| GET | `/api/healthcheck` | General health check |
| GET | `/` | Root endpoint |

---

## Common Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Created successfully |
| 400 | Bad request (invalid data) |
| 401 | Unauthorized (missing/invalid token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Resource not found |
| 422 | Validation error |
| 500 | Internal server error |

---

## Testing Endpoints

### Using Swagger UI
1. Visit `http://localhost:8000/docs`
2. Click endpoint to expand
3. Click "Try it out"
4. Fill parameters
5. Click "Execute"

### Using curl
```bash
# Login
curl -X POST http://localhost:8000/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"user@example.com","password":"password"}'

# Authenticated request
curl -X GET http://localhost:8000/auth/profile \
  -H "Authorization: Bearer your_token_here"