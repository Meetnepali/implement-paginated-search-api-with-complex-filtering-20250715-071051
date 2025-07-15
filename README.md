# Guide to the Project

## Feedback Backend Assessment

This project provides the structure for a FastAPI-based feedback backend system. Your task is to complete and enhance this system according to the requirements below.

### Requirements
- Users must be able to submit feedback with validation and basic profanity filtering.
- Moderators (role-based) must be able to list, approve, or reject feedback via protected endpoints.
- Role-based access control must be enforced using FastAPI dependency injection.
- All status changes (approval/rejection) should trigger background notifications (simulated by logging).
- All key actions (submission, moderation actions, errors) should be logged using structured log entries.
- Feedback data must be stored in memory only.
- Endpoints should be organized using APIRouter and grouped logically.
- User authentication and roles should be simulated via request headers using a dependency.
- No external databases or APIs should be used.

### Verifying Your Solution
- Confirm that feedback cannot be submitted with profanity and is validated appropriately.
- Ensure only users with the moderator role can access moderation endpoints.
- State changes should trigger a visible background log for notification.
- Test endpoint organization, error responses, and log structure via HTTP requests.
- All features should work in-memory and be verifiable with rapid manual or automated testing.
