from datetime import datetime, timezone
from server.app.auth.services import get_user_profile_service
from server.app.db.models.user_models import UserOut


def test_get_profile_returns_fields():
    user = UserOut(
        id="1",
        username="testuser",
        email="test@example.com",
        full_name="Test User",
        bio="Bio",
        location="Loc",
        website="https://example.com",
        avatar_color="#143E6F",
        is_active=True,
        is_verified=False,
        created_at=datetime.now(timezone.utc).isoformat(),
        updated_at=None,
    )

    result = get_user_profile_service(user)

    assert result["username"] == "testuser"
    assert result["email"] == "test@example.com"
    assert result["avatar_color"] == "#143E6F"
